# Java Test Action

This composite action runs tests for a Java microservice using Gradle.

## Inputs

| Input | Description | Default | Required |
|---|---|---|---|
| `java-version` | The Java version to use. | `17` | No |
| `gradle-args` | Arguments to pass to Gradle. | `test` | No |

## Usage

To use this action in your workflow, add the following step:

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Run Java Tests
    uses: Automya/CI-CD-template/actions/java-test@main
    with:
      java-version: '17' # Optional
      gradle-args: 'test' # Optional
```

## Prerequisites

- The repository must contain a valid Gradle wrapper (`gradlew`).
- The project should be a Java project buildable with Gradle.
