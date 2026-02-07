# polinjectum

A simple, transparent, and easy-to-use dependency injection framework for Python.

**polinjectum** gives you inversion of control without the complexity. No XML, no YAML, no classpath scanning, no framework lock-in. Just a Python container that registers callables and resolves them by type — with auto-wiring, lifecycle management, and decorator shortcuts built in.

- Zero external dependencies
- Python 3.8+
- Thread-safe singleton container
- Under 200 lines of core code

## Quick Start

```python
from polinjectum import PolInjectumContainer, Lifecycle

class DatabaseConnection:
    def __init__(self):
        self.connected = True

class UserRepository:
    def __init__(self, db: DatabaseConnection):
        self.db = db

    def find_user(self, user_id: int) -> str:
        return f"User {user_id}"

container = PolInjectumContainer()
container.meet(DatabaseConnection)
container.meet(UserRepository)

repo = container.get_me(UserRepository)  # auto-wires DatabaseConnection
print(repo.find_user(1))                 # "User 1"
print(repo.db.connected)                 # True
```

That's it. `meet` registers, `get_me` resolves. The container inspects `UserRepository.__init__`, sees it needs a `DatabaseConnection`, finds it in the registry, and injects it automatically.

## Installation

```bash
pip install polinjectum
```

For development:

```bash
git clone https://github.com/orlyeac/polinjectum.git
cd polinjectum
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Core Concepts

### The Container

`PolInjectumContainer` is a **singleton**. Every call to `PolInjectumContainer()` returns the same instance. This means you can access the container from anywhere in your application without passing it around:

```python
from polinjectum import PolInjectumContainer

# These are the same object
container_a = PolInjectumContainer()
container_b = PolInjectumContainer()
assert container_a is container_b
```

### Registration with `meet`

`meet` tells the container: "when someone asks for *this type*, use *this factory* to create it."

```python
container.meet(interface, qualifier, factory_function, lifecycle)
```

| Parameter          | Type                | Default                | Description                                         |
|--------------------|---------------------|------------------------|-----------------------------------------------------|
| `interface`        | `type`              | *(required)*           | The type to register under                          |
| `qualifier`        | `str \| None`       | `None`                 | Distinguishes multiple implementations of same type |
| `factory_function` | `Callable \| None`  | `None` (uses interface)| The callable that produces the instance              |
| `lifecycle`        | `Lifecycle`         | `Lifecycle.SINGLETON`  | `SINGLETON` or `TRANSIENT`                          |

If you omit `factory_function`, the `interface` itself is used as the factory. This works naturally when the interface is a concrete class:

```python
container.meet(MyService)  # equivalent to container.meet(MyService, factory_function=MyService)
```

### Resolution with `get_me`

`get_me` retrieves a dependency from the container:

```python
service = container.get_me(MyService)
service = container.get_me(MyService, qualifier="primary")
```

If the type isn't registered, a `ResolutionError` is raised with a clear message showing the full dependency chain that led to the failure.

### Resolution with `get_me_list`

`get_me_list` retrieves **all** registered implementations for a given interface, across all qualifiers:

```python
container.meet(Logger, qualifier="file", factory_function=FileLogger)
container.meet(Logger, qualifier="console", factory_function=ConsoleLogger)

all_loggers = container.get_me_list(Logger)  # [FileLogger instance, ConsoleLogger instance]
```

### Lifecycles

polinjectum supports two lifecycles:

| Lifecycle               | Behavior                                   |
|-------------------------|--------------------------------------------|
| `Lifecycle.SINGLETON`   | One instance, created on first resolution, reused forever (default) |
| `Lifecycle.TRANSIENT`   | New instance created on every `get_me` call |

```python
from polinjectum import Lifecycle

# Singleton: same instance every time
container.meet(Config, lifecycle=Lifecycle.SINGLETON)
assert container.get_me(Config) is container.get_me(Config)  # True

# Transient: fresh instance every time
container.meet(RequestContext, lifecycle=Lifecycle.TRANSIENT)
assert container.get_me(RequestContext) is not container.get_me(RequestContext)  # True
```

### Auto-Wiring

When the container creates an instance, it inspects the constructor's type hints and automatically resolves dependencies from the registry. No annotations or markers needed — just standard Python type hints:

```python
class EmailService:
    pass

class NotificationService:
    def __init__(self, email: EmailService):
        self.email = email

class OrderService:
    def __init__(self, notifications: NotificationService):
        self.notifications = notifications

container.meet(EmailService)
container.meet(NotificationService)
container.meet(OrderService)

order_service = container.get_me(OrderService)
# order_service.notifications is a NotificationService
# order_service.notifications.email is an EmailService
```

Auto-wiring rules:
- Parameters named `self` are skipped
- Parameters without type annotations are skipped
- Parameters with default values are skipped (the default is used instead)
- All other typed parameters are resolved from the container

### Qualifiers

When you have multiple implementations of the same interface, qualifiers let you distinguish between them:

```python
from abc import ABC, abstractmethod

class Cache(ABC):
    @abstractmethod
    def get(self, key: str) -> str: ...

class RedisCache(Cache):
    def get(self, key: str) -> str:
        return f"redis:{key}"

class MemoryCache(Cache):
    def get(self, key: str) -> str:
        return f"memory:{key}"

container.meet(Cache, qualifier="redis", factory_function=RedisCache)
container.meet(Cache, qualifier="memory", factory_function=MemoryCache)

redis = container.get_me(Cache, qualifier="redis")    # RedisCache instance
memory = container.get_me(Cache, qualifier="memory")  # MemoryCache instance
```

### Factory Functions

You don't have to register classes directly. Any callable works — lambdas, functions, classmethods:

```python
# Lambda factory
container.meet(int, qualifier="port", factory_function=lambda: 8080)

# Function factory
def create_database_url() -> str:
    return "postgresql://localhost/mydb"

container.meet(str, qualifier="db_url", factory_function=create_database_url)

# Function factory with logic
def create_logger() -> logging.Logger:
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    return logger

container.meet(logging.Logger, factory_function=create_logger)
```

## Decorators

For a more declarative style, polinjectum provides two decorators.

### `@injectable`

Registers a class with the container at decoration time. Can be used bare or with arguments:

```python
from polinjectum import injectable, Lifecycle

# Bare — registers MyService under MyService as a singleton
@injectable
class MyService:
    pass

# With arguments — registers under a specific interface, qualifier, or lifecycle
@injectable(interface=Cache, qualifier="redis", lifecycle=Lifecycle.TRANSIENT)
class RedisCache(Cache):
    def get(self, key: str) -> str:
        return f"redis:{key}"
```

The class itself is not modified. `@injectable` simply calls `container.meet(...)` behind the scenes and returns the original class.

### `@inject`

Wraps a function so that missing arguments are resolved from the container at call time:

```python
from polinjectum import inject, injectable

@injectable
class Greeter:
    def hello(self, name: str) -> str:
        return f"Hello, {name}!"

@inject
def greet_user(greeter: Greeter) -> str:
    return greeter.hello("World")

# Call without arguments — greeter is resolved from the container
print(greet_user())  # "Hello, World!"

# Call with explicit argument — your value takes precedence
custom_greeter = Greeter()
print(greet_user(greeter=custom_greeter))  # "Hello, World!"
```

`@inject` only resolves parameters that:
1. Were **not** supplied by the caller
2. Have a **type annotation**
3. Match a **registered type** in the container

Unregistered types are left alone (the function will raise `TypeError` if they're required and missing, just like normal Python).

## Error Handling

polinjectum provides clear error messages with dependency chain information.

### `RegistrationError`

Raised when registration is invalid:

```python
from polinjectum import PolInjectumContainer, RegistrationError

container = PolInjectumContainer()

try:
    container.meet(str, factory_function=42)  # not callable
except RegistrationError as e:
    print(e)  # "factory_function must be callable, got int"
```

### `ResolutionError`

Raised when a dependency cannot be resolved. Includes the full resolution chain to help you trace the problem:

```python
from polinjectum import PolInjectumContainer, ResolutionError

class Database:
    pass

class Repository:
    def __init__(self, db: Database):
        self.db = db

container = PolInjectumContainer()
container.meet(Repository)
# Forgot to register Database!

try:
    container.get_me(Repository)
except ResolutionError as e:
    print(e)
    # "Cannot auto-wire parameter 'db' of type Database (resolution chain: Database)"
    print(e.chain)  # ["Database"]
```

## Advanced Examples

### Layered Architecture

A typical web application with repository, service, and controller layers:

```python
from polinjectum import PolInjectumContainer, injectable

@injectable
class PostgresConnection:
    def __init__(self):
        self.url = "postgresql://localhost/myapp"

    def execute(self, query: str) -> list:
        return [{"id": 1, "name": "Alice"}]

@injectable
class UserRepository:
    def __init__(self, conn: PostgresConnection):
        self.conn = conn

    def find_all(self) -> list:
        return self.conn.execute("SELECT * FROM users")

@injectable
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def list_users(self) -> list:
        return self.repo.find_all()

@injectable
class UserController:
    def __init__(self, service: UserService):
        self.service = service

    def handle_list_request(self) -> dict:
        return {"users": self.service.list_users()}

# The entire dependency graph is resolved automatically
container = PolInjectumContainer()
controller = container.get_me(UserController)
print(controller.handle_list_request())
# {"users": [{"id": 1, "name": "Alice"}]}
```

### Interface Segregation with Abstract Base Classes

Program against interfaces, register concrete implementations:

```python
from abc import ABC, abstractmethod
from polinjectum import PolInjectumContainer, Lifecycle

class MessageSender(ABC):
    @abstractmethod
    def send(self, to: str, body: str) -> bool: ...

class SmtpSender(MessageSender):
    def send(self, to: str, body: str) -> bool:
        print(f"SMTP -> {to}: {body}")
        return True

class SmsSender(MessageSender):
    def send(self, to: str, body: str) -> bool:
        print(f"SMS -> {to}: {body}")
        return True

container = PolInjectumContainer()
container.meet(MessageSender, qualifier="email", factory_function=SmtpSender)
container.meet(MessageSender, qualifier="sms", factory_function=SmsSender)

# Resolve a specific implementation
email_sender = container.get_me(MessageSender, qualifier="email")
email_sender.send("alice@example.com", "Hello!")

# Resolve all implementations and broadcast
for sender in container.get_me_list(MessageSender):
    sender.send("bob@example.com", "Broadcast message")
```

### Testing with `reset()`

The container provides `reset()` to clear all registrations between tests:

```python
import unittest
from polinjectum import PolInjectumContainer

class TestMyService(unittest.TestCase):
    def setUp(self):
        PolInjectumContainer.reset()
        self.container = PolInjectumContainer()

    def tearDown(self):
        PolInjectumContainer.reset()

    def test_with_real_dependency(self):
        self.container.meet(Database, factory_function=Database)
        self.container.meet(UserService)
        service = self.container.get_me(UserService)
        assert service is not None

    def test_with_mock(self):
        mock_db = MockDatabase()
        self.container.meet(Database, factory_function=lambda: mock_db)
        self.container.meet(UserService)
        service = self.container.get_me(UserService)
        assert service.db is mock_db
```

### Configuration Values with Factories

Use qualifiers and lambdas to inject configuration:

```python
import os
from polinjectum import PolInjectumContainer

container = PolInjectumContainer()

container.meet(str, qualifier="db_host", factory_function=lambda: os.getenv("DB_HOST", "localhost"))
container.meet(int, qualifier="db_port", factory_function=lambda: int(os.getenv("DB_PORT", "5432")))
container.meet(str, qualifier="db_name", factory_function=lambda: os.getenv("DB_NAME", "myapp"))

host = container.get_me(str, qualifier="db_host")
port = container.get_me(int, qualifier="db_port")
```

### Mixing Auto-Wired Dependencies with Extra Parameters

In real applications, classes often need both registered dependencies *and* configuration values or runtime parameters. The factory function is your tool for bridging the two — it captures the extra arguments while letting the container resolve the rest.

**Default values for configuration, auto-wiring for services:**

The simplest approach. Parameters with defaults are skipped by auto-wiring, so the container resolves the service dependencies and the defaults provide the configuration:

```python
from polinjectum import PolInjectumContainer

class ConnectionPool:
    def __init__(self, max_size: int = 10, timeout: float = 30.0):
        self.max_size = max_size
        self.timeout = timeout

class UserRepository:
    def __init__(self, pool: ConnectionPool, table_name: str = "users"):
        self.pool = pool
        self.table_name = table_name

container = PolInjectumContainer()
container.meet(ConnectionPool)
container.meet(UserRepository)

repo = container.get_me(UserRepository)
print(repo.pool.max_size)   # 10 (default)
print(repo.table_name)      # "users" (default)
```

**Factory functions that override defaults:**

When you need different configuration than the defaults, wrap the constructor in a factory that supplies the extra parameters. The factory itself can receive auto-wired arguments:

```python
from polinjectum import PolInjectumContainer

class ConnectionPool:
    def __init__(self, max_size: int = 10, timeout: float = 30.0):
        self.max_size = max_size
        self.timeout = timeout

class UserRepository:
    def __init__(self, pool: ConnectionPool, table_name: str = "users"):
        self.pool = pool
        self.table_name = table_name

container = PolInjectumContainer()

# Register the pool with custom config via a factory
container.meet(ConnectionPool, factory_function=lambda: ConnectionPool(max_size=50, timeout=5.0))

# Register the repo with a factory that takes the auto-wired pool
# and adds the extra parameter
def create_user_repo(pool: ConnectionPool) -> UserRepository:
    return UserRepository(pool, table_name="app_users")

container.meet(UserRepository, factory_function=create_user_repo)

repo = container.get_me(UserRepository)
print(repo.pool.max_size)   # 50 (custom)
print(repo.pool.timeout)    # 5.0 (custom)
print(repo.table_name)      # "app_users" (custom)
```

Note how `create_user_repo` has a typed `pool` parameter — the container auto-wires it, while `table_name` is supplied directly inside the factory.

**Multiple implementations with different configuration:**

Combine qualifiers with factory functions to register several variants of the same type, each with its own parameters:

```python
from polinjectum import PolInjectumContainer

class HttpClient:
    def __init__(self, base_url: str, timeout: float, retries: int):
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries

    def get(self, path: str) -> str:
        return f"GET {self.base_url}{path}"

container = PolInjectumContainer()

container.meet(
    HttpClient,
    qualifier="payments",
    factory_function=lambda: HttpClient("https://payments.api.com", timeout=10.0, retries=3),
)
container.meet(
    HttpClient,
    qualifier="users",
    factory_function=lambda: HttpClient("https://users.api.com", timeout=5.0, retries=1),
)

payments_client = container.get_me(HttpClient, qualifier="payments")
users_client = container.get_me(HttpClient, qualifier="users")

print(payments_client.get("/charge"))  # "GET https://payments.api.com/charge"
print(users_client.get("/profile"))    # "GET https://users.api.com/profile"
print(payments_client.retries)         # 3
print(users_client.retries)            # 1
```

**Factory functions that combine registered and runtime values:**

A factory can pull some values from the container and combine them with hardcoded or computed values:

```python
import os
from polinjectum import PolInjectumContainer

class Logger:
    def __init__(self, name: str, level: str):
        self.name = name
        self.level = level

    def log(self, msg: str) -> None:
        print(f"[{self.level}] {self.name}: {msg}")

class DatabaseConnection:
    def __init__(self, host: str, port: int, logger: Logger):
        self.host = host
        self.port = port
        self.logger = logger

    def connect(self) -> str:
        self.logger.log(f"Connecting to {self.host}:{self.port}")
        return f"{self.host}:{self.port}"

container = PolInjectumContainer()

# Register the logger with extra parameters via factory
container.meet(Logger, factory_function=lambda: Logger("app", "INFO"))

# The database factory auto-wires Logger from the container
# and adds host/port from environment variables
def create_db_connection(logger: Logger) -> DatabaseConnection:
    return DatabaseConnection(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        logger=logger,
    )

container.meet(DatabaseConnection, factory_function=create_db_connection)

db = container.get_me(DatabaseConnection)
db.connect()  # [INFO] app: Connecting to localhost:5432
```

The key insight: **factory functions are auto-wired too**. Any typed parameter in a factory function's signature is resolved from the container, so you get the best of both worlds — automatic injection for registered dependencies and manual control for everything else.

## Comparison with Other DI Frameworks

| Feature                    | polinjectum         | dependency-injector | inject          | python-inject   |
|----------------------------|---------------------|---------------------|-----------------|-----------------|
| Zero dependencies          | Yes                 | No (requires C ext) | No              | No              |
| Lines of core code         | ~200                | ~10,000+            | ~500            | ~300            |
| Auto-wiring                | Yes (type hints)    | No (explicit)       | Yes             | Yes             |
| Learning curve             | Minutes             | Hours               | Minutes         | Minutes         |
| Decorator registration     | Yes                 | No                  | Yes             | Yes             |
| Thread-safe                | Yes                 | Yes                 | No              | Yes             |
| Lifecycle management       | Singleton/Transient | Multiple            | Singleton only  | Singleton only  |
| Qualifier support          | Yes                 | Yes                 | No              | No              |
| Error messages             | Dependency chain    | Stack trace         | Stack trace     | Stack trace     |

**Why polinjectum?**

- **You want DI without a framework.** polinjectum is a library, not a framework. It doesn't dictate your architecture.
- **You want to understand the code.** The entire implementation fits in a single file. There's no metaclass sorcery, no descriptor protocol abuse, no import hooks.
- **You want to get started in minutes.** Three methods (`meet`, `get_me`, `get_me_list`) and two decorators (`@injectable`, `@inject`). That's the whole API.
- **You don't want extra dependencies.** Pure Python, nothing to install beyond the package itself.

## API Reference

### `PolInjectumContainer`

| Method                                          | Description                              |
|-------------------------------------------------|------------------------------------------|
| `meet(interface, qualifier?, factory_function?, lifecycle?)` | Register a dependency                    |
| `get_me(interface, qualifier?) -> Any`          | Resolve a single dependency              |
| `get_me_list(interface) -> list`                | Resolve all implementations of a type    |
| `reset()` *(classmethod)*                       | Clear all registrations (for testing)    |

### `Lifecycle`

| Value        | Behavior                        |
|--------------|---------------------------------|
| `SINGLETON`  | Same instance always (default)  |
| `TRANSIENT`  | New instance each time          |

### Decorators

| Decorator                                        | Description                                           |
|--------------------------------------------------|-------------------------------------------------------|
| `@injectable`                                    | Register class under itself as singleton               |
| `@injectable(interface=T, qualifier=Q, lifecycle=L)` | Register class with specific options              |
| `@inject`                                        | Auto-resolve missing typed args at call time           |

### Exceptions

| Exception           | Raised When                                  |
|---------------------|----------------------------------------------|
| `RegistrationError` | Factory is not callable                      |
| `ResolutionError`   | Type not registered or auto-wiring fails     |

## Contributing

Contributions are welcome. Please follow these guidelines:

1. Fork the repository and create a feature branch from `develop`
2. Write tests for any new functionality
3. Ensure all tests pass: `pytest tests/ -v --cov=polinjectum`
4. Maintain test coverage above 90%
5. Follow PEP 8 style and add type hints to all function signatures
6. Submit a pull request to `develop`

## License

MIT License. See [LICENSE](LICENSE) for details.
