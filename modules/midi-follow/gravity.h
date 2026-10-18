#ifndef BF_GRAVITY_H
#define BF_GRAVITY_H
int bf_context_c(unsigned track);
int bf_epoch_c(unsigned context);
int bf_mode_c(unsigned track);
int bf_home_c(unsigned track);
int bf_source_c(unsigned track);
int bf_resolve_c(unsigned track);
int bf_gravity_c(int pitch_class, unsigned track);
void bf_sync_c(unsigned track);
void bf_begin_c(unsigned track);
void bf_sent_c(unsigned track);
void bf_reset_c(void);
void bf_forget_c(unsigned track);
#endif
