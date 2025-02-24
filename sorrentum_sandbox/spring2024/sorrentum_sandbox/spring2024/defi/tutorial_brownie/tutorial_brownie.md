# Brownie

- Brownie is a Python-based development and testing framework for smart contracts
  targeting the Ethereum VM
- It's equivalent to `Truffle` / `Hardhat` but using Python instead of JavaScript
- Documentation is at: https://eth-brownie.readthedocs.io/en/stable
- `Brownie` allows to:
  - deploy contracts
  - interact with contracts on mainnet or local testnet
  - debug contracts
  - unit test contracts

# Brownie tutorials

- These are the files needed for the tutorials:
  ```
  + tree --dirsfirst -n -F --charset unicode tutorial_brownie
  tutorial_brownie/
  |-- hello_world_contract/
  |   |-- build/
  |   |   |-- contracts/
  |   |   |   `-- SimpleContract.json
  |   |   |-- deployments/
  |   |   |-- interfaces/
  |   |   `-- tests.json
  |   |-- contracts/
  |   |   `-- hello_world_contract.sol
  |   |-- interfaces/
  |   |-- reports/
  |   |-- scripts/
  |   |-- tests/
  |   `-- brownie-config.yaml
  |-- proj_files/
  |   |-- brownie-config.yaml
  |   |-- deploy.py*
  |   |-- deploy_interact.py
  |   |-- goerli.json
  |   |-- hello_world_contract.sol
  |   |-- interact.py
  |   |-- surre_token_v1.sol
  |   `-- surre_token_v2.sol
  |-- bake_token1.ipynb
  |-- bake_token1.sh*
  |-- hello_world_contract.ipynb
  |-- hello_world_contract.sh*
  |-- surre_token1.ipynb
  |-- surre_token1.sh*
  `-- tutorial_brownie.txt
  ```

- All the tutorials need to start `Jupyter` and `Ganache`
  ```
  > cd $GIT_ROOT/defi
  > devops/docker_bash.sh
  docker> /data/devops/run_ganache.sh

  # Go to a new terminal.
  > devops/docker_exec.sh
  docker> /data/devops/run_jupyter.sh
  ```

- On your local computer point the browser to `localhost:8889` and you should see
  Jupyter running

- Note that `defi/tutorial_brownie` in the Git repo is mapped to the `/data`
  directory in the container 

- For each Jupyter notebook, you want to execute each cell one-by-one and make
  sure you understand what's going on
  - Also play with the code to build your mental model

## `Hello world` tutorial

### Description

- This tutorial was inspired by this [on-line
  article](https://betterprogramming.pub/part-1-brownie-smart-contracts-framework-for-ethereum-basics-5efc80205413)
  - Create a simple "hello world" contract
  - Run the `Brownie` toolchain (compile, test)
  - Deploy on local blockchain with Ganache
  - Exercise the contract

### Compile and test

- Besides running `Jupyter` and `Ganache`, let's start another shell in the same
  container to run `Brownie`
  ```
  > devops/docker_exec.sh
  docker> cd /data/tutorial_brownie
  docker> ls -1
  bake_token1.ipynb
  bake_token1.sh
  hello_world_contract
  hello_world_contract.ipynb
  ...
  ```

- The script running the tutorial is `defi/tutorial_brownie/hello_world_contract.sh`
  ```
  docker> vi defi/tutorial_brownie/hello_world_contract.sh
  ```
  and performs the following phases:
  - Create a Brownie project
  - Copy files to complete the project
  - Compile the contract
  - Run the tests

- Take a look at the contract that we want to compile and run:
  ```
  docker> more proj_files/hello_world_contract.sol
  pragma solidity ^0.5.11;

  contract SimpleContract {
       uint value;
       function setValue(uint _value) external {value = _value;}
       function getValue() external view returns(uint){return value;}
  }
  ```

- Create the Brownie project:
  ```
  docker> brownie init

  docker> find .
  .
  ./.gitattributes
  ./.gitignore
  ./build
  ./build/contracts
  ./build/deployments
  ./build/interfaces
  ./contracts
  ./interfaces
  ./reports
  ./scripts
  ./tests
  ```

- Copy the files from the project in the right location

- Compile the contract with `brownie compile`
- The output looks like:
  ```
  + cd /data/tutorial_brownie/hello_world_contract
  + brownie init
  Brownie v1.19.2 - Python development framework for Ethereum

  SUCCESS: A new Brownie project has been initialized at /data/tutorial_brownie/hello_world_contract
  + cp -r /data/tutorial_brownie/proj_files/hello_world_contract.sol /data/tutorial_brownie/hello_world_contract/contracts
  + cp -r /data/tutorial_brownie/proj_files/brownie-config.yaml /data/tutorial_brownie/hello_world_contract
  + brownie compile
  Brownie v1.19.2 - Python development framework for Ethereum

  Compiling contracts...
    Solc version: 0.5.17
    Optimizer: Enabled  Runs: 200
    EVM Version: Istanbul
  Generating build data...
   - SimpleContract

  Project has been compiled. Build artifacts saved at /data/tutorial_brownie/hello_world_contract/build/contracts
  + brownie test
  Brownie v1.19.2 - Python development framework for Ethereum

  ======================================================================================== test session starts =========================================================================================
  platform linux -- Python 3.10.6, pytest-6.2.5, py-1.11.0, pluggy-1.0.0
  rootdir: /data/tutorial_brownie/hello_world_contract
  plugins: eth-brownie-1.19.2, forked-1.4.0, hypothesis-6.27.3, xdist-1.34.0, web3-5.31.1
  collected 0 items
  ======================================================================================= no tests ran in 0.06s ========================================================================================
  ```

- There are no tests to run
  - TODO(gp): Add some tests

- Several files are generated in the dir `hello_world_contract`, which you want
  to take a look at to understand what's going on
  ```
  > $GIT_ROOT/dev_scripts/tree.sh defi/tutorial_brownie/hello_world_contract
  + tree --dirsfirst -n -F --charset unicode defi/tutorial_brownie/hello_world_contract
  defi/tutorial_brownie/hello_world_contract/
  |-- build/
  |   |-- contracts/
  |   |   `-- SimpleContract.json
  |   |-- deployments/
  |   |-- interfaces/
  |   `-- tests.json
  |-- contracts/
  |   `-- hello_world_contract.sol
  |-- interfaces/
  |-- reports/
  |-- scripts/
  |-- tests/
  `-- brownie-config.yaml
  ```

### Run

- You can run the notebook
  `http://localhost:8889/notebooks/data/tutorial_brownie/hello_world_contract.ipynb`
  to exercise the contract
  - You want to execute each cell one-by-one and make sure you understand what's
    going on
  - The notebook shows how to perform transactions, deploy the contract, exercise
    the contract

- You can use `Brownie` console to create a REPL Python console similar to
  IPython
  ```
  docker> cd hello_world_contract
  docker> brownie console --network development

  Brownie v1.19.2 - Python development framework for Ethereum

  ProjProject is the active project.
  Attached to local RPC client listening at '127.0.0.1:8545'...
  Brownie environment is ready.
  >>> type(SimpleContract)
  <class 'brownie.network.contract.ContractContainer'>
  ```

- You can also run the code directly in a Python script `hello_world_contract.py`
- E.g.,
  ```
  import brownie
  brownie.network.connect('development')
  myproject = brownie.project.load('/data/tutorial_brownie/hello_world_contract')
  print("SimpleContract=", myproject.SimpleContract)
  ```
- The output looks like:
  ```
  > hello_world_contract.py
  Attached to local RPC client listening at '127.0.0.1:8545'...
  SimpleContract= <brownie.network.contract.ContractContainer object at 0x7f103eddae30>
  ```

## `bake_token` tutorial

### Description

- The GitHub project is (here)[https://github.com/brownie-mix/token-mix]
- It is a simple implementation of ERC20 token in Solidity

### Testnet set-up
- To use the Goerli testnet account you need to generate a keystore with:
  ```
  docker> brownie accounts new goerli
  Brownie v1.19.2 - Python development framework for Ethereum

  Enter the private key you wish to add: ...
  Enter the password to encrypt this account with: ...
  SUCCESS: A new account '0x980D0Ca15A31aB8157CF0F108Dfa250192dc77b4' has been generated with the id 'goerli'

  docker> cp ~/.brownie/accounts/goerli.json /data/tutorial_brownie/proj_files/goerli.json
  ```
- You need to use MetaMask to extract the private key and put some Goerli Ether
  in the account to transact

- You also need an Infura node
  ```
  export WEB3_INFURA_PROJECT_ID=...
  ```

### Compile and test

- Create the project
  ```
  > ./bake_token1.sh
  ```

- The Brownie project is downloaded and looks like:
  ```
  > /Users/saggese/src/cmamp1/dev_scripts/tree.sh bake_token1
  + tree --dirsfirst -n -F --charset unicode bake_token1
  bake_token1/
  |-- build/
  |   |-- contracts/
  |   |   |-- SafeMath.json
  |   |   `-- Token.json
  |   |-- deployments/
  |   `-- interfaces/
  |-- contracts/
  |   |-- SafeMath.sol
  |   `-- Token.sol
  |-- interfaces/
  |-- reports/
  |-- scripts/
  |   `-- token.py
  |-- tests/
  |   |-- conftest.py
  |   |-- test_approve.py
  |   |-- test_transfer.py
  |   `-- test_transferFrom.py
  |-- LICENSE
  |-- README.md
  |-- brownie-config.yaml
  `-- requirements.txt
  ```

- The contract is under `bake_token1/contracts/Token.sol`

- Follow the example in https://eth-brownie.readthedocs.io/en/stable/index.html
- The notebook is: http://localhost:8888/notebooks/data/tutorial_brownie/bake_token1.ipynb


- Run with
  ```
  docker> bake_token1.sh
  ```

## `surrentum_token1`

### Description

- Create a token in proj_files/openzeppelin_token.sol
  - Mintable
  - Burnable
  - Pausable

### Compile and test

- Create the project
  ```
  > ./surrentum_token1.sh
  ```
- In practice the project is the same as `bake token` but with an ERC20 token
  from openzeppelin

### Run

- The notebook is `http://localhost:8889/notebooks/data/tutorial_brownie/surre_token1.ipynb`

# References

// https://chainstack.com/the-brownie-tutorial-series-part-1/
// GitHub: https://github.com/SethuRamanOmanakuttan/brownie-tutorial-series
// https://betterprogramming.pub/part-1-brownie-smart-contracts-framework-for-ethereum-basics-5efc80205413
