// The real first-sector PIO routine, with a completion interrupt requested
// at its final data word. Firmware bytes are always read from local files.
#include "machine.h"
#include "mc68k/Musashi/m68k.h"
#include "mc68k/cpuState.h"
#include <cstdio>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

namespace {
std::vector<uint8_t> read(const char* path) {
    std::ifstream f(path, std::ios::binary);
    if(!f) return {};
    return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}

bool run(const std::vector<uint8_t>& image, const std::vector<uint8_t>& runtime,
         uint32_t base, unsigned mask, bool guarded) {
    ot::Machine m(image);
    auto* cpu = m.getCpuState();
    constexpr uint32_t stack = 0x46010000, buffer = 0x46020000;
    constexpr uint32_t returned = 0x40000400, irq = 0x41000000;
    for(size_t i = 0; i < runtime.size(); ++i) m.write8(base + i, runtime[i]);
    for(unsigned i = 0; i < 256; ++i) m.write16(buffer + 2*i, i ^ 0xa55a);
    m.write32(0x46c8c594, buffer);
    m.write8(0x46c8c592, 1);
    m.write32(stack, 0x11223344);             // d2 saved by the stock prologue
    m.write32(stack + 4, 0x55667788);         // d3 saved by the stock prologue
    m.write32(stack + 8, returned);
    m.write32(0xb6 * 4, irq);
    m.write16(irq, 0x4e73);                  // test interrupt: rte
    m68k_set_reg(cpu, M68K_REG_VBR, 0);
    unsigned words = 0, acks = 0, remainingAtAck = 999;
    uint32_t pointerAtAck = 0;
    bool samplesOK = true;
    m.setAckHook([&](uint8_t vector, uint8_t level) {
        ++acks;
        samplesOK &= vector == 0xb6 && level == 5;
        remainingAtAck = m.read8(0x46c8c592);
        pointerAtAck = m.peek32(0x46c8c594);
    });
    m.setPeripheralHandlers([&](uint32_t addr, uint8_t, uint32_t& out) {
        if(addr != 0x900000d8) return false;
        out = words < 256 ? 0x58 : 0x50;     // DRQ goes away at completion
        return true;
    }, [&](uint32_t addr, uint8_t size, uint32_t value) {
        if(addr != 0x900000a0) return;
        samplesOK &= size == 2 && value == (words ^ 0xa55a);
        if(++words == 256) m.injectInterrupt(0xb6, 5);
    });
    m68k_set_reg(cpu, M68K_REG_SR, 0x2000 | (mask << 8));
    m68k_set_reg(cpu, M68K_REG_SP, stack);
    m68k_set_reg(cpu, M68K_REG_D2, 1);        // requested sector count
    m.setPC(0x40014cdc);                     // stock SR save, before WRITE
    bool stepsOK = true;
    for(unsigned n = 0; n < 20000 && m.pc() != returned; ++n) {
        if(!m.step()) { stepsOK = false; break; }
    }
    const bool delivered = mask < 5;
    const bool bookkeeping = !delivered ||
        (remainingAtAck == (guarded ? 0u : 1u) &&
         pointerAtAck == buffer + (guarded ? 512u : 0u));
    const bool ok = stepsOK && m.pc() == returned && words == 256 && samplesOK &&
        acks == unsigned(delivered) && bookkeeping &&
        m.read8(0x46c8c592) == 0 && m.peek32(0x46c8c594) == buffer + 512 &&
        (m68k_get_reg(cpu, M68K_REG_SR) & 0x2700) == (0x2000 | (mask << 8)) &&
        m68k_get_reg(cpu, M68K_REG_D0) == 1 &&
        m68k_get_reg(cpu, M68K_REG_D2) == 0x11223344 &&
        m68k_get_reg(cpu, M68K_REG_D3) == 0x55667788 &&
        m68k_get_reg(cpu, M68K_REG_SP) == stack + 12;
    std::printf("  [%s] %s IPL=%u: %u words, %u completion IRQ(s), remaining at IRQ %u, pointer %#x%s\n",
                ok ? "PASS" : "FAIL", guarded ? "guard" : "stock control", mask,
                words, acks, remainingAtAck, pointerAtAck, stepsOK ? "" : m.why().c_str());
    return ok;
}
}

int main(int argc, char** argv) {
    if(argc != 5) {
        std::fprintf(stderr, "usage: ata_write_probe STOCK IMAGE RUNTIME BASE\n");
        return 2;
    }
    const auto stock = read(argv[1]), image = read(argv[2]), runtime = read(argv[3]);
    if(stock.empty() || image.empty() || runtime.empty()) {
        std::fprintf(stderr, "ATA write test: missing local firmware/runtime input\n");
        return 2;
    }
    const auto base = static_cast<uint32_t>(std::stoul(argv[4], nullptr, 0));
    bool ok = run(stock, {}, 0, 0, false);   // must reproduce stock's window
    for(unsigned mask : {0u, 1u, 3u, 5u, 7u})
        ok = run(image, runtime, base, mask, true) && ok;
    return ok ? 0 : 1;
}
