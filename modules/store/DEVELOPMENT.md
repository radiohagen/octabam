# STORE contribution verification

The STORE-client integration additionally checks native-copy success and
failure, clobbering callback registers, first-error short-circuiting, all
native load caller/mask combinations, and full-capacity retained restart and
NEW PROJECT under the port. `verify_store_copy.py` is STORE's image gate;
`verify_harmony_store.py` and `verify_harmony_load_hooks.py` are Harmony's.
The optional client machinery compiles out for all eight original client
combinations. The one shared behavior correction is that a failed native
copy no longer dispatches companion-copy notifications.
