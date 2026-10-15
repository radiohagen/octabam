/* Entry frames remain exactly those of stock. Harmony's explicit bridge
 * continuations chain to unmodified P2 handlers; native work runs once. */
    .text
    .global hpl_ch_step_encoder,hpl_ch_memcpy
hpl_ch_step_encoder:
    tst.l 0x80000012
    beq.s .audio
    jmp ch_step_encoder
.audio:
    jmp plk_edit
hpl_ch_memcpy: jmp ch_memcpy
