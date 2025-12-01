# NPM Test Action

This composite action runs tests for a React frontend using NPM.

## Inputs

| Input | Description | Default | Required |
|---|---|---|---|
| `node-version` | The Node.js version to use. | `18` | No |
| `npm-args` | Arguments to pass to `npm run`. | `test` | No |
| `install-command` | Command to install dependencies. | `npm ci` | No |

## Usage

To use this action in your workflow, add the following step:

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Run NPM Tests
    uses: Automya/CI-CD-template/actions/npm-test@main
    with:
      node-version: '18' # Optional
      npm-args: 'test' # Optional
      install-command: 'npm ci' # Optional
```

## Prerequisites

- The repository must contain a valid `package.json` and `package-lock.json`.
- The project should be a Node.js project.
