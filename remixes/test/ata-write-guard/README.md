# ata-write-guard

Stock effects with [ATA WRITE GUARD](../../../modules/ata-write-guard/README.md).
The module's gate forces the interrupt that races the first sector's
bookkeeping in stock. Port checks only; not on a unit.

```
make check REMIX=ata-write-guard
```
