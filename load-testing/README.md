1. Setup venv in this folder and install requirements.

2. To authenticate with the api you need a bearer token. The easiest way to get one is to open playground.allenai.org check the network tab and pull the value of the "authorization" header from an api request. Make a .env file and put that in. Leave off the word bearer.

```
USER_TOKEN=asdfasdfadsfasdfasdfasdf
```

3. Run

```sh
  locust
```

Then launch the web ui by pressing enter. At the moment a pod can handle about 8 "users" in this ui. So factor that in.

4.  Add https://playground.allenai.org url for prod
