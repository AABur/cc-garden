# Abstract Factory

**TL;DR:** Provide a way to encapsulate a group of individual factories that share a
common theme, without specifying their concrete classes.

**Category:** Creational

## When to use

- You need to create *families* of related objects and the family must vary together
  (e.g., a `WindowsTheme` factory that produces `WindowsButton`, `WindowsCheckbox`,
  `WindowsScrollbar`; a `MacTheme` factory producing the Mac-flavoured trio). The
  invariant is "all products from one factory belong to the same family".
- The choice of family is made *once*, at the application's edge (config, CLI flag,
  feature toggle), and propagates throughout the program.
- You want client code to be agnostic to which concrete classes it instantiates — only
  the abstract product interfaces.

## When NOT to use (Pythonic alternatives first)

- **Single product type, multiple variants.** That is the simpler `Factory` pattern;
  see `creational/factory.md`.
- **Class is already first-class.** In Python, classes *are* callables, so a factory is
  often *just the class itself*. `PetShop(Cat)` works because `Cat(name)` is a valid
  call. Adding an `AbstractCatFactory` interface above `Cat` is ceremony.
- **Just one place chooses the family.** A `dict[str, type]` lookup at the boundary is
  enough.
- **Families do not share an interface.** If `WindowsButton` and `MacButton` have
  different methods, you do not have a family — you have unrelated classes.

## Canonical implementation

From `faif/python-patterns` (`patterns/creational/abstract_factory.py`):

```python
from typing import Type

class Pet:
    def __init__(self, name: str) -> None: self.name = name
    def speak(self) -> None: raise NotImplementedError

class Dog(Pet):
    def speak(self) -> None: print("woof")

class Cat(Pet):
    def speak(self) -> None: print("meow")

class PetShop:
    def __init__(self, animal_factory: Type[Pet]) -> None:
        self.pet_factory = animal_factory

    def buy_pet(self, name: str) -> Pet:
        return self.pet_factory(name)

cat_shop = PetShop(Cat)
pet = cat_shop.buy_pet("Lucy")
pet.speak()  # "meow"
```

The "factory" is a class object passed in. No `AnimalFactory` ABC is needed because
classes are callable and Python uses duck typing.

## Real-world examples

- **Django storage backends.** `DEFAULT_FILE_STORAGE` selects a class; all file
  operations go through that class's interface. Switching backend swaps a family of
  related operations.
- **`logging.Handler` subclasses.** A configured logger picks a handler class; the
  handler's "family" is its formatter, filters, and emit method.
- **GUI toolkits** (Qt themes, ttk styles): one theme produces a coordinated set of
  styled widgets.

## Refactor recipe

When you have a sprawling `if platform == "win": ... elif platform == "mac": ...`:

1. Identify the *product family* — the related classes that change together.
2. Extract each family into a module or namespace (`win/`, `mac/`).
3. At the application edge, pick the module: `theme = win if platform == "win" else mac`.
4. Pass `theme` (or specific classes from it) to constructors that need products.
5. Delete the conditional dispatch from the body of the program.

In Python, "the factory" is often a *module* with the same public names. No abstract
base classes required.

## Review checklist

- ✅ The family of products genuinely varies together; switching one without the others
  would break invariants.
- ✅ The choice of family is made in one place (boundary) and threaded through.
- ❌ The "abstract factory" wraps a single class — that is just `Factory` (or just the
  class itself).
- ❌ The factory is a class hierarchy with one method that returns a class. In Python
  this is almost always over-engineered; pass the class directly.
- ❌ Products from different "families" are mixed at runtime — the pattern's invariant
  is broken; reach for `Factory` or `Strategy` instead.
