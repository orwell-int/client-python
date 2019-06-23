# python-client

## Description

Client that forwards inputs to, and visualisation data from the game server.

## Requirements

Python 2.7
zmq
protobuf (v2)
make

## Usage

Get and install dependencies and create virtual environment.
```
make develop
```

On raspbery pi, run the program with:
```
sudo make start
```

Test with unittests that things work.
```
make test
```
