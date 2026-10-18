A card-write path: stock's initial PIO write could hang polling the card
after a task switch; the guard keeps its critical section intact.
Measured under the port; cursory testing on Sam's MKII (owner report,
16 Oct 2026). Nothing on the panel.
