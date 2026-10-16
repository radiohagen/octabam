# PIO first-sector test remix

[PIO WRITE FIX](../../../modules/pio-write-fix/README.md) alone on stock effects.
It has no recording menu or STEM REC task.

```
make check REMIX=pio-write-fix
```

The installed-hook gate includes the unpatched stock ordering as a negative
control and checks immediate card-handler state, data and register preservation.
Full application project-save/reload tests remain a separate integration gate;
this isolated proof does not establish physical-card or DMA behavior.
