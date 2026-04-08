### Go Requirements

Some features require the Go programming language to be installed.

**Version Required:**
```bash
# Check Go version
go version
# Should show Go 1.24 or higher
```

**Installing Go:**

=== "Linux"
    ```bash
    # Download and install latest Go
    wget https://go.dev/dl/go1.24.0.linux-amd64.tar.gz
    sudo rm -rf /usr/local/go
    sudo tar -C /usr/local -xzf go1.24.0.linux-amd64.tar.gz

    # Add to PATH
    echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
    source ~/.bashrc

    # Verify installation
    go version
    ```

=== "macOS"
    ```bash
    # Using Homebrew
    brew install go

    # Or download from https://go.dev/dl/
    # Install the .pkg file and restart terminal

    # Verify installation
    go version
    ```

=== "Windows"
    ```powershell
    # Download installer from https://go.dev/dl/
    # Run the .msi installer
    # Restart terminal

    # Verify installation
    go version
    ```

**Configure GOPATH:**
```bash
# Set GOPATH (usually automatic)
export GOPATH=$HOME/go
export PATH=$PATH:$GOPATH/bin
```

See [Go's official installation guide](https://go.dev/doc/install) for more details.
