# Guard expression code generation

Generate C callback bodies for all seven declarative Horcrux guards through the existing code generation language layer.

## 1. Parse and bind expressions

- [ ] Reuse the validated AST from `expressions.parse()`. Start with boolean context fields, boolean operators, numeric literals and comparisons, named constants, and enum equality and inequality.
- [ ] Bind context fields and constants using the same lookup precedence as the Python evaluator. Resolve bare enum members from the comparison operand's type so each use of `none` binds to the correct enum.
- [ ] Check operand and guard result types before emission. Report unsupported syntax, ambiguous enum members, and incompatible operands with the machine name, guard name, and expression text.
- [ ] Keep the bound expression representation independent of the target language so future backends and setters can reuse it.

## 2. Emit C through the language layer

- [ ] Add a guard expression emission hook to the existing language layer. Delegate the C implementation to an emitter that operates on bound expressions.
- [ ] Reuse C naming rules for enum members and match the generated spelling of context fields and constants.
- [ ] Preserve expression grouping and short-circuit evaluation. Support chained comparisons only when their semantics can be preserved and verified.

## 3. Generate guard callbacks

- [ ] Register a companion `c_machine_src` template. Bind and emit the guard expressions before rendering and make the included header name configurable.
- [ ] Emit one definition per guard with an `expr`, using the existing `(state_machine, user_ctx)` callback signature. Keep declarations in the generated header and supply hardware-dependent guards such as `SelfNoisePresent` in handwritten C.
- [ ] Reuse the existing transition table composition for compound and negated guard references.

## 4. Verify the Horcrux output

- [ ] Generate the header and source through the normal command, then compile and link with stubs for handwritten guards and actions.
- [ ] Compare all seven generated guard callbacks with the Python evaluator. Cover both enums' `none` members, values immediately below and at the attempt threshold, and a transition that composes or negates a guard.
- [ ] Check that ambiguous and incompatible expressions produce clear generation errors.

## Follow-up

- [ ] Reuse the binder for setters, using the destination type to resolve enum members. Define the fixed-width integer overflow policy before emitting arithmetic assignments.
