# Version-specific gameplay data

`catalog-2.0.77.json` contains recipe and technology facts exported from base Factorio 2.0.77 during the historical experiment. It contains no game assets or executable game code. Run ticks and player-force `enabled`/`researched` state were removed for publication.

`client.materials` uses the deterministic early solid-item recipe subset. Technology energy is recorded in game ticks; recipe energy is in seconds. Recipe availability must be observed in the actual game, not inferred from this catalog. Re-export and validate metadata when changing Factorio versions.

Factorio is a product of Wube Software. This project is an independent experiment and does not distribute Factorio itself.
