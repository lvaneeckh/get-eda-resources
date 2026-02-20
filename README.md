# Get EDA Resources

The `get-eda-resources` script is designed to fetch Nokia EDA resources using the k8s API (via `kubectl`) and soon will also support `edactl`. The script is intended to be used to fetch resources from a specified namespace to easily re-create them in another cluster or namespace. It differs from the native EDA backup and restore functionality by allowing to fetch only EDA resources from a namespace, without fetching all other resource and without backing up the git.

## Installation

The script requires [`uv` to be installed](https://docs.astral.sh/uv/getting-started/installation/).

## Usage

```
./get-eda-resources --namespace <namespace>
```

> The derived resources are not fetched by this script.

This command will fetch all EDA resources from the specified namespace and save them in a directory named `eda-resources/<namespace>`.

### Flags

- `--namespace` (required): The namespace from which to fetch EDA resources.
- `--output-dir` (optional): The directory where the fetched resources will be saved. Default is `eda-resources`.
- `--archive` (optional): If set, the fetched resources will be saved in a tar.gz archive next to the files in a directory.
- `--set-namespace` (optional): If set, the namespace of the fetched resources will be changed to the specified namespace. This is useful when applying the resources to a different namespace.
- `--group` (optional): The group of the resource to fetch. If not specified, all EDA resources (containing `.eda.nokia.com` in their API group) will be fetched.

## Applying Fetched Resources

To apply the fetched resources to another cluster or namespace, you can use [the `etc` script](https://github.com/eda-labs/etc-script/) until `edactl` is available as a native binary.
