
# Testing


## Setup 
Two ways of runnnings tests...
### e2e
Requires a fully working app and has real world side effects. 

```
docker compose exec api pytest -m "not integration"
```

All e2e tests should live in the e2e folder.

### Unit & Integration Tests
This setup extends unit tests to also have access to the database. To run them you need to install postgres.

```sh
brew install postgresql
```

In the python .venv you can simply run these tests by writing 

```sh
export FLASK_CONFIG_PATH="test.config.json" && pytest --ignore e2e --ignore src/attribution
```

Integration Tests can be placed anywhere in the app. 


## Fixtures
These new tests leverage pytest fixtures to give you access to a database.

This database is isolated to just a single tests, so you don't need to clean anything up and you don't have to worry about other test messing things up.

To use the database simple add the following fixtures to your tests.

```python
class TestDatabase:
    def test_thread_setup(self, sql_alchemy: Session): # <-- This line 
        message_repo = MessageRepository(sql_alchemy)
```

Fixtures key off of name and are automatically added to your test.

So `sql_alchemy` var will get you the sql_alchemy session for this test.

I also added `dbc` fixture which will give you access to the old Client. We are moving away from using the dbc client in the backend but this is here if you need it.

These fixtures are set up to automatically add the "integration" mark to your test if used.

This database is pre populated from our sql files
01-local.sql
02-schema.sql
03-add_models.sql


#### Future fixtures
Feel free to add fixtures for anything that would be helpful for testing, and is used across many tests. You can make fixtures live across a whole session or be rerun for every test.

Fixtures can be a nice way to setup data in the session database.
Fixtures can be also be used to mock other services within the app.


## VScode Debugging pytests

There is now a script in vscode to run debug on a given test file, simply set breakpoints anywhere then return to the test file. 

## VScode Test runner
With the microsoft python package
https://marketplace.visualstudio.com/items?itemName=ms-python.python

You can also use the test runner, which appears as a beaker on the left side bar in vscode. Should work out of the box.
