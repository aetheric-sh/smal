# CHANGELOG


## v0.3.6 (2026-04-01)

### Bug Fixes

- Fix bug with detecting machine root when it is ephemeral
  ([#28](https://github.com/aetheric-sh/smal/pull/28),
  [`6aeb256`](https://github.com/aetheric-sh/smal/commit/6aeb25636039858b04c08b2be4c942af9c9148d0))


## v0.3.5 (2026-04-01)

### Bug Fixes

- Minor tweaks to diagramming logic ([#27](https://github.com/aetheric-sh/smal/pull/27),
  [`9dfb93c`](https://github.com/aetheric-sh/smal/commit/9dfb93c36adf5e1a2b3bfad4114d78b3bd387432))

- Hides composite root to root-level state transitions from diagramming - Actually disables the no
  transitions to root-level initial state rule


## v0.3.4 (2026-04-01)

### Bug Fixes

- Minor diagramming fixes ([#26](https://github.com/aetheric-sh/smal/pull/26),
  [`adfb65f`](https://github.com/aetheric-sh/smal/commit/adfb65fefafc35bd5afab01084deed17db91403f))

* update example diagram

- Minor diagramming fixes ([#26](https://github.com/aetheric-sh/smal/pull/26),
  [`adfb65f`](https://github.com/aetheric-sh/smal/commit/adfb65fefafc35bd5afab01084deed17db91403f))


## v0.3.3 (2026-04-01)

### Bug Fixes

- Allow for multiple incoming/outgoing ephemeral transitions within composite nodes
  ([#25](https://github.com/aetheric-sh/smal/pull/25),
  [`bafe57b`](https://github.com/aetheric-sh/smal/commit/bafe57bac25d16fcd411cc552044c2766dcb715e))


## v0.3.2 (2026-04-01)

### Bug Fixes

- Utilize automatic ephemeral initial states in diagramming
  ([#24](https://github.com/aetheric-sh/smal/pull/24),
  [`fae71fa`](https://github.com/aetheric-sh/smal/commit/fae71fa54568ca093d28481a95ed13bb6ec9c67f))

- Adds `corrections` to automatically correct common shorthands/issues in .smal files, similar to
  `rules` - Automatically creates ephemeral initial state nodes in diagrams to preserve labels on
  the user-intended initial states.


## v0.3.1 (2026-04-01)

### Bug Fixes

- Get uv.lock in step with pyproject.toml
  ([`1842f0f`](https://github.com/aetheric-sh/smal/commit/1842f0fb57ddddb8c1bf49c9c6cc46dd814bd51e))


## v0.3.0 (2026-04-01)

### Features

- Align schemas, enhance CLI and code generation
  ([#23](https://github.com/aetheric-sh/smal/pull/23),
  [`cac8a1a`](https://github.com/aetheric-sh/smal/commit/cac8a1abe188e80c7ece493465f8d2a6860f6fdc))

* stub remaining commands

* update workspace settings

* Cleanup all existing schemas

* remove main.py

* Fix imports

fix errors

* Everything works but validate cmd

fix validate

* cleanup console styling

* working on validators for states and state machines

* working on implementations

* Added rules engine

* cleaned up cli

* Added a lot of C macros

* finished macros for now

* remove test files

* done for now, added ephemeral initial states


## v0.2.3 (2026-03-30)

### Bug Fixes

- Implement substates for SMALState ([#22](https://github.com/aetheric-sh/smal/pull/22),
  [`5464b56`](https://github.com/aetheric-sh/smal/commit/5464b5652d427d7cb86443d87abef96d376ce843))

* Got substates and diagramming for it working

* update launch.json

* revert uv lock change


## v0.2.2 (2026-03-30)

### Bug Fixes

- New app workflow works with protected branches
  ([`f65d148`](https://github.com/aetheric-sh/smal/commit/f65d148a1eea8513aedada1649419657ebe11a11))


## v0.2.1 (2026-03-30)

### Bug Fixes

- Testing new workflow with app ([#21](https://github.com/aetheric-sh/smal/pull/21),
  [`d843cc2`](https://github.com/aetheric-sh/smal/commit/d843cc22afab4c07c33b447ad9cf559275c73391))


## v0.2.0 (2026-03-30)

### Features

- Update broken org links
  ([`b859d1e`](https://github.com/aetheric-sh/smal/commit/b859d1e482bb9dc9e1c5c34fb329f54f13c33e5b))


## v0.1.0 (2026-03-30)

### Bug Fixes

- Add build cmd ([#17](https://github.com/aetheric-sh/smal/pull/17),
  [`719dece`](https://github.com/aetheric-sh/smal/commit/719dece366d23c602263215e5efa978470ad60ae))

- Add debug logs to workflow
  ([`9651bf0`](https://github.com/aetheric-sh/smal/commit/9651bf0c5254fad1f2e94d29e53450205e659eed))

- Another workflow update
  ([`854afa1`](https://github.com/aetheric-sh/smal/commit/854afa168fb4a96a3299d3704a62986c47af7a29))

- Another workflow update ([#18](https://github.com/aetheric-sh/smal/pull/18),
  [`2fdcdaf`](https://github.com/aetheric-sh/smal/commit/2fdcdaf998c5f75aaaa903e98a18a4f0fbc7a896))

- Bump version
  ([`38c8506`](https://github.com/aetheric-sh/smal/commit/38c850661f28e244da9ac73739bb877612e83251))

- Correct commit message
  ([`095e13f`](https://github.com/aetheric-sh/smal/commit/095e13f6e6f899f728685de1c090516822be2570))

- Give semantic release a PAT ([#12](https://github.com/aetheric-sh/smal/pull/12),
  [`b652668`](https://github.com/aetheric-sh/smal/commit/b6526687450b02cb496aeace410a724997f81fed))

- Install uv during release
  ([`8ce49eb`](https://github.com/aetheric-sh/smal/commit/8ce49eb083b96402d7454e8302bffafdb116c6b5))

- One more workflow change ([#13](https://github.com/aetheric-sh/smal/pull/13),
  [`4b50c6d`](https://github.com/aetheric-sh/smal/commit/4b50c6d3084621611bc64f55c8e28ca06f376112))

- Only build new version
  ([`2c95226`](https://github.com/aetheric-sh/smal/commit/2c952268b2dfa189d73e2388c5165103ff49fc98))

- Pypi not seeing dist
  ([`7fc3d78`](https://github.com/aetheric-sh/smal/commit/7fc3d78b6d18ca5fe7cf5ee1c690e058d838a766))

- Re-add outputs
  ([`8dfa8e2`](https://github.com/aetheric-sh/smal/commit/8dfa8e2c159cea00e5bd53fcd5d721a88d8216e9))

- Test 13 ([#14](https://github.com/aetheric-sh/smal/pull/14),
  [`ac83ece`](https://github.com/aetheric-sh/smal/commit/ac83ecec996502570dac56cd567d0d158eb77efa))

- Test 14 ([#15](https://github.com/aetheric-sh/smal/pull/15),
  [`7fbd1f7`](https://github.com/aetheric-sh/smal/commit/7fbd1f727da990d218dfbabf4447838b02abc7c5))

- Test 15 ([#16](https://github.com/aetheric-sh/smal/pull/16),
  [`989d8d0`](https://github.com/aetheric-sh/smal/commit/989d8d0d683e0a984a7e9c45cf97e7e0efeca975))

- Testing debug logs
  ([`4e6bbe0`](https://github.com/aetheric-sh/smal/commit/4e6bbe0273d990e787da38986f8112b72711783d))

- Update badge links in README.md
  ([`f27b0c2`](https://github.com/aetheric-sh/smal/commit/f27b0c2494662ba0d6215db449315304c6146bf0))

- Update project links and badges in README
  ([`b4bb4a3`](https://github.com/aetheric-sh/smal/commit/b4bb4a3434132731ecb6d7580a3d15dfcb23c1aa))

- Update pyproject.toml and workflow ([#11](https://github.com/aetheric-sh/smal/pull/11),
  [`4cac6ba`](https://github.com/aetheric-sh/smal/commit/4cac6ba21b29cc02c4f84bd51ca595a56e122584))

- Update readme
  ([`6f15046`](https://github.com/aetheric-sh/smal/commit/6f15046e869af10e0745bc48ba7478b8fe087d2c))

- Update uv build cmd ([#19](https://github.com/aetheric-sh/smal/pull/19),
  [`c751e09`](https://github.com/aetheric-sh/smal/commit/c751e09beb3274dc2e63bf2e239ff4f7ad79aa27))

- Uv build cmd
  ([`a1defdd`](https://github.com/aetheric-sh/smal/commit/a1defdde438dc755de1412ea9497a29cf486d186))

- Working on last bit
  ([`09f8858`](https://github.com/aetheric-sh/smal/commit/09f8858216254fe272a4f2e27822eae84f7f7975))

### Features

- Update readme.md ([#20](https://github.com/aetheric-sh/smal/pull/20),
  [`d632baf`](https://github.com/aetheric-sh/smal/commit/d632baf968cdf7e23ef756493b613c0f11152ab4))

* remove debugging line in workflow

- Update readme.md ([#20](https://github.com/aetheric-sh/smal/pull/20),
  [`d632baf`](https://github.com/aetheric-sh/smal/commit/d632baf968cdf7e23ef756493b613c0f11152ab4))
