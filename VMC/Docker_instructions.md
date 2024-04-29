# Docker Instructions
### This guide is for building/running Docker containers outside of the Jetson's enviroment
## Docker setup
- First, [install Docker Desktop](https://docs.docker.com/desktop/install/windows-install/)
- Then, run `pip install docker` if you haven't yet
- If you want to build/run Docker images **NOT** on a Jetson, run this command once first:

    ```bash
    docker run --rm --privileged docker.io/multiarch/qemu-user-static --reset -p yes
    ```
<br/>

## Building and running containers

Make sure you're in the VMC directory so you can run start.py

**IMPORTANT**: Use `start.py -h` to see full syntax & config options

### You'll need to build the containers through start.py before running them:
```bash
start.py build {Container Name(s)}
```

Note: If you update a VMC module you'll need to rebuild it

### Then simulate running the containers you want using this command:
```bash
start.py -s run {Container Name(s)}
```

Finally open up docker desktop and take a look at your glorious new container <br/>
You can also run `app.py` in the GUI folder and connect to your container <br/>

<br/>

If you're in a hurry, here's the only command you'll ever need:
```bash
start.py -s run sandbox fcm
```
### Misc:

**Note that the apriltag container will fail to build, and everything except Sandbox and FCM will fail to simulate properly due to missing peripherals** <br/><br/>
If you have any questions come to Max