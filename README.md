# How to add a new application to parcelLab

## Setting up your repository

### Add repository to `repos.yaml`

Add the repository to [`repos.yaml`](https://github.com/parcelLab/plconfig/blob/main/repos.yaml) with a regular pull request, following best practices for pull requests in parcelLab. Once your change hits the `main` branch, the new repository will be created through the [Repos workflow](https://github.com/parcelLab/plconfig/actions/workflows/repos.yaml).

### Set correct name

In your new repository, search for all occurences of the default name "repo-template-base" and replace it with the name of your repository.

### Write Containerfile

Your application will need a Containerfile to be deployed. Add your code (ideally in a `src/` folder) and modify the `Containerfile` in the repository to start the application. Look at other applications using the same software stack to get a sense of the best practices in parcelLab for doing so.

### Configure tests

Modify `.github/workflows/test.yaml` in your repository to start the correct tests for your application.

### Update other files

Update `CODEOWNERS`, `CONTRIBUTING.md`, `README.md`, `.github/dependabot.yml` to suit your applications needs.

## Deploy

### Deploy to test cluster

Change the `Chart.yaml` and `values.yaml` in `.chart/test` to suit your application, in particular the health and ready check. Make sure the port is set to one your application listens on.

Add your application to [`values.test.yaml`](https://github.com/parcelLab/infrastructure/blob/main/charts/apps/workloads/values.test.yaml) in the infrastructure repository with a regular pull request, following best practices for pull requests at parcelLab.

Also run the "Deployment" action in your repository with environment set to "test" and the branch pointed to "main".

Once the pull request is merged and your "Deployment" action has completed, your application will be deployed to the test cluster, where you can inspect it via [ArgoCD](https://argocd.test.parcellab.dev).

### Deploy to staging cluster

The process is analogous to deployment to the test cluster.

### Deploy to production

Add your application to [`values.prod.yaml`](https://github.com/parcelLab/infrastructure/blob/main/charts/apps/workloads/values.prod.yaml), analogous to the process for test and staging.

Deployment itself is handled via releases.

The "Release" workflow automatically creates and updates a draft release whenever you make changes to the "main" branch. To publish a release, navigate to the Releases section of your repository and publish the automatically generated draft release.
