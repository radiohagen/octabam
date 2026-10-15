// Synthetic loader hash and real-spin regressions; no firmware input.
#include "machine.h"
#include "mc68k/Musashi/m68k.h"
#include "mc68k/cpuState.h"
#include <cstdio>
#include <vector>

int main()
{
    int failed = 0;
    const auto check = [&](const char* name, bool ok) {
        std::printf("[%s] %s\n", ok ? "PASS" : "FAIL", name);
        if(!ok) ++failed;
    };
    const std::vector<uint8_t> code = {
        0x72,0x00, 0x24,0x01, 0xeb,0x89, 0xd2,0x82, 0x74,0x00,
        0x14,0x18, 0xd2,0x82, 0x53,0x80, 0x66,0x00,0xff,0xf0, 0x4e,0x40
    };
    for(bool alternate : {false, true}) {
        auto image = code;
        if(alternate) image[4] = 0xe9; // Shift by four: a different finite read loop.
        uint32_t hash = 0;
        for(uint32_t i = 0; i < 300000; ++i) {
            image.push_back(uint8_t(i)); hash = hash * (alternate ? 17 : 33) + uint8_t(i);
        }
        ot::Machine m(image);
        m68k_set_reg(m.getCpuState(), M68K_REG_D0, 300000);
        m68k_set_reg(m.getCpuState(), M68K_REG_A0, 0x40000400 + code.size());
        const auto stop = m.run(3000000);
        check(alternate ? "finite alternate read loop reaches handoff" : "large loader hash reaches handoff",
            stop == ot::Machine::Stop::Handoff);
        check("every byte hashed without skipping instructions", m.getD(1) == hash && m.getD(0) == 0);
    }
    ot::Machine spin(std::vector<uint8_t>{0x60,0xfe});
    check("true spin still faults", spin.run(3000000) == ot::Machine::Stop::Fault);
    ot::Machine limited(code);
    m68k_set_reg(limited.getCpuState(), M68K_REG_D0, 300000);
    check("instruction budget still enforced", limited.run(100) == ot::Machine::Stop::Budget);
    return failed ? 1 : 0;
}
