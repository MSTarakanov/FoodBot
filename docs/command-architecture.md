# Command architecture

This document explains how a Telegram update becomes a FoodBot command response.
Use it together with `CONTRIBUTING.md` when adding or changing commands.

## Package responsibilities

- `commanding/` owns the reusable slash-command lifecycle, catalog, access checks,
  common errors, and command protocols.
- `commands/` owns one concrete slash command per file. A command coordinates
  dependencies but does not own persistence or reusable business rules.
- `flows/` owns the reusable conversational flow engine and transitions.
- `features/<name>/` owns feature models, errors, repositories, use cases,
  rendering, callbacks, and feature-specific flows.
- `application/` owns policies shared by multiple features, such as resolving an
  active user.
- `bootstrap/` constructs long-lived command, flow, service, and repository
  instances and injects their dependencies.

Do not store update-specific data on command instances. The catalog reuses the
same command objects for concurrent Telegram updates; per-update state belongs in
`CommandContext` or an FSM `FlowSession`.

## Slash-command lifecycle

```text
Telegram Message
  -> CommandDispatcher
     -> parse invocation and resolve CommandCatalog entry
     -> apply flow reset policy
     -> check CommandDefinition scope/admin access
     -> build CommandContext
  -> Command.handle
     -> ordered context validators
     -> parser: raw arguments -> typed input variant
     -> ordered request validators
     -> resolver: typed input -> semantic request
     -> execute command-specific behavior
  -> BotMessenger
```

The stages have separate responsibilities:

- `CommandDefinition` describes name, aliases, help/menu metadata, static scope,
  admin access, flow policy, and input-error messages.
- A context validator checks facts that do not depend on arguments, for example
  Telegram identity or active registration.
- A parser classifies syntax without loading data or performing effects.
- A request validator checks access that depends on the parsed variant.
- A resolver converts syntax into a semantic request and returns `InputErrorCode`
  for expected input failures.
- A use case or feature service performs authoritative business checks and effects.
- A renderer converts a typed model into a Telegram payload. It does not load data.

Validators run in tuple order and stop after the first failure. Dependencies are
passed explicitly through constructors in
[`commands/factory.py`](../src/office_food_bot/commands/factory.py).

## Choosing a command type

| Type | Use when | Result |
| --- | --- | --- |
| `RenderedCommand` | One request produces one model and one reply | `Model -> MessagePayload` |
| `ResultRenderedCommand` | The feature can return typed expected errors | `Result[Model, FeatureError]` |
| `EffectCommand` | The operation sends multiple messages, polls, notifications, or schedules work | Effects are explicit in `execute_effect` |
| `FlowCommand` | The operation starts a multi-message conversation | Delegates to `FlowRunner` |

Do not introduce another base-class combination for a special case. A concrete
command can inherit directly from the lowest suitable contract and delegate
complex behavior to a feature use case.

## Errors

Expected errors are handled at the layer that understands them:

- dispatcher and validators return `CommonErrorCode`;
- resolvers return `InputErrorCode` rendered from `CommandDefinition`;
- feature use cases return their feature error enum and use their feature renderer;
- application errors are mapped to command errors at the command/transport boundary;
- unexpected database, Telegram, and programming exceptions reach the global
  error handler, which logs the exception and returns a safe internal-error text.

Finite enums are handled with exhaustive `match` and `assert_never`. Do not use
runtime type registries or `isinstance` dispatch for error rendering.

## Example: `/hi`

Source: [`commands/hi.py`](../src/office_food_bot/commands/hi.py).

`HiCommand` is the smallest `EffectCommand`:

1. `CommandDefinition` makes it available in any chat.
2. `NoArgumentsParser` creates `NoArguments`.
3. There are no command-specific validators.
4. `IdentityResolver` passes the request through unchanged.
5. `execute_effect` remembers the Telegram profile when available, writes a log,
   and replies through `BotMessenger`.

It is an effect command rather than a rendered command because it performs work
beyond producing a response model.

## Example: `/approve 123456789`

Source: [`commands/approve.py`](../src/office_food_bot/commands/approve.py).

`ApproveCommand` demonstrates a typed administrative effect:

1. The dispatcher enforces private-chat and `admin_only` access from the definition.
2. `TelegramIdentityValidator` requires an actor identity.
3. `ApproveRequestParser` preserves the raw user-id argument in `ApproveInput`.
4. `ApproveRequestResolver` requires a positive decimal id and creates
   `ApproveRequest`.
5. `execute_effect` calls `RegistrationService.approve`.
6. The service performs the authoritative permission check before changing data.
7. The command replies to the admin and notifies the approved user.

Security-sensitive services re-check permission even if the dispatcher already
checked it. Transport access improves UX; the service check protects the action.

## Example: `/coffee`

Sources: [`commands/coffee.py`](../src/office_food_bot/commands/coffee.py),
[`features/coffee/`](../src/office_food_bot/features/coffee), and
[`features/coffee/controller.py`](../src/office_food_bot/features/coffee/controller.py).

`CoffeeCommand` demonstrates one command with several typed variants:

```text
no argument       -> CoffeeStatusInput   -> CoffeeStatusRequest
on/off            -> CoffeeToggleInput   -> CoffeeToggleRequest
minutes or HH:MM  -> CoffeeScheduleInput -> CoffeeScheduleRequest
```

The flow is:

1. Context validators require Telegram identity and an active user.
2. `CoffeeRequestParser` classifies the variant.
3. `CoffeeScheduleScopeValidator` requires a group only for scheduling; status
   and invitation toggles remain available in private chat.
4. `CoffeeRequestResolver` resolves and validates the schedule time.
5. `execute_effect` delegates status, invitation settings, or scheduling to the
   corresponding feature service and renderer.

Buttons on a coffee card are not slash commands. `CoffeeCallbackController`
unpacks typed callback data, resolves the active user, calls the same coffee
service, and answers the callback with common or coffee-specific error rendering.
The controller is registered separately in
[`commands/router.py`](../src/office_food_bot/commands/router.py).

## Example: `/register`

Sources: [`commands/register.py`](../src/office_food_bot/commands/register.py),
[`features/registration/flow/`](../src/office_food_bot/features/registration/flow),
and [`flows/`](../src/office_food_bot/flows).

`RegisterCommand` is a `FlowCommand`:

1. `RegisterRequestParser` classifies self-registration and admin registration
   of another Telegram id.
2. `RegisterOtherAdminValidator` applies admin access only to the second variant.
3. `RegisterRequestResolver` creates a typed `RegisterRequest`.
4. `FlowRunner.start` clears the previous flow and calls `RegistrationFlow.start`.
5. The flow creates `RegistrationDraft` and returns `MoveToStep(NAME, ...)`.
6. `FlowRunner` stores `FlowSession(flow_id, step_id, draft)` in aiogram FSM state
   and publishes the step view.

For every following user message:

```text
FlowRunner
  -> RegistrationFlow resolves the current FlowStep by enum id
  -> step parser
  -> ordered step validators
  -> step.advance
  -> StayOnStep | MoveToStep | CompleteFlow
```

`StayOnStep` keeps state and repeats a validation view. `MoveToStep` stores the
new typed draft and next step. `CompleteFlow` clears state, removes the reply
keyboard when needed, and can run a typed post-action such as notifying admins.
`/cancel` delegates cancellation to the active flow through `FlowRunner`.

Registration steps are assembled in
[`features/registration/flow/factory.py`](../src/office_food_bot/features/registration/flow/factory.py).
Each step owns its parser and validators; cross-step decisions and completion
belong to `RegistrationFlowUseCase`.

## Adding the next command

1. Define typed input and request models.
2. Choose the command type from the table above.
3. Add ordered context and variant validators.
4. Keep syntax in the parser and semantic conversion in the resolver.
5. Put feature behavior, models, errors, and rendering under `features/<name>/`.
6. Register the constructed command in `commands/factory.py`.
7. Register callbacks, polls, or background adapters separately in the router.
8. Test the pipeline through the dispatcher and unit-test parsers, resolvers,
   services, flows, and renderers at their own boundaries.
9. Run `scripts/check`.
