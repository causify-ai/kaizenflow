#!/usr/bin/env python3
import brownie

brownie.network.connect("development")
myproject = brownie.project.load("/data/tutorial_brownie/hello_world_contract")

print("SimpleContract=", myproject.SimpleContract)
