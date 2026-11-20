# Guard expression code generation

Generate C callback bodies for all seven declarative Horcrux guards through the existing code generation language layer.

## 1. Parse and bind expressions

- [x] Reuse the validated AST from `expressions.parse()`. Start with boolean context fields, boolean operators, numeric literals and comparisons, named constants, and enum equality and inequality.
- [x] Bind context fields and constants using the same lookup precedence as the Python evaluator. Resolve bare enum members from the comparison operand's type so each use of `none` binds to the correct enum.
- [x] Check operand and guard result types before emission. Report unsupported syntax, ambiguous enum members, and incompatible operands with the machine name, guard name, and expression text.
- [x] Keep the bound expression representation independent of the target language so future backends and setters can reuse it.

## 2. Emit C through the language layer

- [x] Add a guard expression emission hook to the existing language layer. Delegate the C implementation to an emitter that operates on bound expressions.
- [x] Reuse C naming rules for enum members and match the generated spelling of context fields and constants.
- [x] Preserve expression grouping and short-circuit evaluation. Chained comparisons and mixed floating-point and integer comparisons are deferred.

## 3. Generate guard callbacks

- [x] Register a companion `c_machine_src` template. Bind and emit the guard expressions before rendering. The include defaults to `c_machine_hdr.h` and can be set with `metadata.c_header_filename`.
- [x] Emit one definition per guard with an `expr`, using the existing `(state_machine, user_ctx)` callback signature. Keep declarations in the generated header and supply hardware-dependent guards such as `SelfNoisePresent` in handwritten C.
- [x] Reuse the existing transition table composition for compound and negated guard references.

## 4. Verify the Horcrux output

- [ ] Generate the header and source through the normal command, then compile and link with stubs for handwritten guards and actions.
- [ ] Compare all seven generated guard callbacks with the Python evaluator. Cover both enums' `none` members, values immediately below and at the attempt threshold, and a transition that composes or negates a guard.
- [ ] Check that ambiguous and incompatible expressions produce clear generation errors.

## Follow-up

- [x] Reuse the binder for setters, using the destination type to resolve enum members. Emit setter callbacks in assignment order.
- [x] Check narrowing writes before assignment. Generated C calls `SMAL_SETTER_RANGE_ERROR()` on failure, which defaults to `abort()`. If an override returns, the action exits before the failing write and any remaining assignments.
- [ ] Extend arithmetic support to expressions whose intermediate values cannot be proven to fit in a signed 64-bit integer.
