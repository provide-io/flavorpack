#!/bin/bash

set -e

go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
go install golang.org/x/tools/cmd/goimports@latest
go install honnef.co/go/tools/cmd/staticcheck@latest
go install github.com/securego/gosec/v2/cmd/gosec@latest
go install github.com/go-critic/go-critic/cmd/gocritic@latest
go install github.com/jgautheron/goconst/cmd/goconst@latest
go install github.com/kisielk/errcheck@latest
go install github.com/mdempsky/unconvert@latest
go install github.com/gordonklaus/ineffassign@latest
go install github.com/fzipp/gocyclo/cmd/gocyclo@latest
go install github.com/client9/misspell/cmd/misspell@latest
