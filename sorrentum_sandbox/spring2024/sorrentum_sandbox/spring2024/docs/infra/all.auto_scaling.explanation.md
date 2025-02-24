# Auto Scaling Explanation

## Table of Contents

<!-- toc -->

- [Introduction](#introduction)
- [Cluster Autoscaler (CA)](#cluster-autoscaler-ca)
  * [CA Configuration Highlights](#ca-configuration-highlights)
- [Auto Scaling Group (ASG)](#auto-scaling-group-asg)
  * [ASG Integration with Kubernetes](#asg-integration-with-kubernetes)
- [Horizontal Pod Autoscaler (HPA)](#horizontal-pod-autoscaler-hpa)
  * [HPA Configuration Highlights](#hpa-configuration-highlights)
- [Workflow Overview](#workflow-overview)
- [Conclusion](#conclusion)

<!-- tocstop -->

## Introduction

Auto Scaling ensures that the applications maintain performance and manage costs
effectively by automatically adjusting the number of computing resources in use
based on demand. In Kubernetes environments, this capability is crucial for
handling workload spikes, improving resource utilization, and maintaining
application availability. This document outlines the implementation of Auto
Scaling in the Kubernetes setup, focusing on the Cluster Autoscaler (CA),
Horizontal Pod Autoscaler (HPA), and Auto Scaling Groups (ASG).

## Cluster Autoscaler (CA)

The Cluster Autoscaler dynamically adjusts the number of nodes in a Kubernetes
cluster to meet the current workload demands. It increases the number of nodes
during high demand periods and decreases them when the demand drops, ensuring
optimal cost efficiency and resource utilization.

### CA Configuration Highlights

CA monitors the demand on the Kubernetes cluster and communicates with AWS ASGs
to scale the number of nodes in the cluster. It ensures that there are enough
nodes to run all pods without significant overprovisioning. If pods fail to
launch due to lack of resources, CA will request ASG to add more nodes.
Conversely, if nodes are underutilized, CA will scale down the ASG to remove
excess nodes, optimizing costs. Generally, a node is considered underutilized if
it has been running below a certain threshold of resource usage (e.g., CPU,
memory) for a specific period. Cluster Autoscaler uses various metrics,
including resource requests versus usage, to identify underutilization. These
thresholds and periods are configurable. By default, CA considers a node
underutilized if it has been running at low capacity (below 50% CPU utilization)
for a predefined period (10 minutes).

The deployment configuration for the Cluster Autoscaler is defined in
[`cluster-autoscaler-autodiscover.yaml`](/infra/kubernetes/airflow/templates/ca/cluster-autoscaler-autodiscover.yaml).
This configuration ensures that the Cluster Autoscaler monitors node groups
tagged for Auto Scaling and adjusts them based on the workload requirements. Key
points in this configuration include:

- **Auto-discovery of node groups**: The Cluster Autoscaler is configured to
  automatically discover node groups tagged with specific labels indicating they
  are enabled for Auto Scaling within the Kubernetes cluster environment.
- **Expander Strategy**: The `least-waste` expander strategy is used, which aims
  to minimize resource wastage by choosing the node group that would leave the
  smallest amount of CPU and memory unused after a scale-up event.

## Auto Scaling Group (ASG)

Auto Scaling Groups (ASG) in AWS provide a mechanism to automatically adjust the
number of EC2 instances within the set to match the load on the application. ASG
ensures that the application has the right amount of capacity to handle the
current demand level.

### ASG Integration with Kubernetes

Although ASG operates at the EC2 instance level, its integration with the
Kubernetes Cluster Autoscaler allows for a seamless scaling experience. When the
Cluster Autoscaler determines that a cluster needs to grow, it requests the ASG
to launch additional EC2 instances. Conversely, when nodes are underutilized,
the Cluster Autoscaler can signal the ASG to terminate instances, ensuring
efficient resource use.

- **Tag-based Discovery**: The Cluster Autoscaler discovers ASGs through
  specific tags, enabling it to manage the scaling of nodes within those groups
  automatically.
- **Scaling Actions**: Based on the workload requirements and current cluster
  state, the CA sends commands to the ASG to either increase or decrease the
  number of nodes in the cluster, ensuring that the number of nodes always
  aligns with the workload needs.

## Horizontal Pod Autoscaler (HPA)

The Horizontal Pod Autoscaler automatically scales the number of pods in a
replication controller, deployment, or replica set based on observed CPU and
memory usage. This means it can adjust the number of pods in a deployment to
meet the workload demands.

### HPA Configuration Highlights

The HPA configuration, as defined in
[`scheduler-hpa.yaml`](/infra/kubernetes/airflow/templates/hpas/scheduler-hpa.yaml),
targets the `airflow-scheduler` deployment within the `airflow` namespace. It
adjusts the number of pods based on CPU and memory utilization, with the aim to
maintain these usages near 90%. This ensures that the scheduler component of
Airflow has sufficient resources to handle workload variations efficiently. The
configuration specifics are:

- **Scaling Targets**: It targets the `airflow-scheduler` deployment, with a
  scaling range between 1 to 6 replicas based on the demand.
- **Resource Utilization**: Utilization targets for both CPU and memory are set
  to 90%, enabling the HPA to add or remove pods to maintain this level of
  utilization. This means if the CPU/Mem usage of the Airflow Schedulers reaches
  90% of the requested resources, HPA will automatically increase the number of
  scheduler pod replicas to distribute the load more evenly.

## Workflow Overview

The workflow of Cluster Autoscaler (CA), Auto Scaling Groups (ASG), and
Horizontal Pod Autoscaler (HPA) within a Kubernetes cluster forms a
comprehensive auto-scaling solution that dynamically adjusts both the number of
pods and nodes based on the workload demands.

1. **Monitoring Resource Demands**: The HPA monitors the CPU and memory usage of
   pods against the defined targets. Simultaneously, the CA monitors for pods
   that cannot be scheduled due to insufficient resources.

2. **Horizontal Pod Autoscaler (HPA) Reaction**:

   - If the HPA detects that the CPU or memory usage of the pods exceeds or
     falls below the configured thresholds, it triggers a scale-out or scale-in
     action for the pods within the target deployment (e.g., increasing or
     decreasing the number of replicas of the Airflow Scheduler).

3. **Cluster Autoscaler (CA) Reaction**:

   - If new pods cannot be scheduled because there are not enough resources in
     the cluster, the CA identifies this and decides to scale up the number of
     nodes.
   - Conversely, if the CA detects that some nodes are underutilized and their
     pods can be placed on fewer nodes, it triggers a scale-down action, safely
     evicting pods and terminating excess nodes.

4. **Auto Scaling Groups (ASG) Execution**:

   - When the CA decides to scale up, it communicates with the cloud provider's
     ASG to add more nodes into the cluster.
   - For scaling down, it selects nodes to remove, ensures pods are safely
     evicted to other nodes, and then reduces the node count in the ASG.

5. **New Nodes Joining the Cluster**:

   - As new nodes are provisioned by the ASG, they join the Kubernetes cluster,
     becoming available resources for scheduling pods.

6. **Rebalancing and Optimization**:

   - With the addition of new nodes, the HPA might adjust the number of pod
     replicas again, based on the now-available resources and the target
     utilization rates.
   - The CA continually monitors for opportunities to optimize the distribution
     of pods across nodes, including the possibility of scaling down if
     resources are underutilized.

7. **Continuous Monitoring**:
   - Both HPA and CA continuously monitor the cluster's state and workload
     demands, ready to adjust the number of pods or nodes as needed to meet the
     set targets for resource utilization and efficiency.

This orchestrated workflow of HPA, CA, and ASG ensures that Kubernetes clusters
are dynamically scalable, self-healing, and efficient, meeting both current and
future demands with minimal manual intervention.

## Conclusion

Auto Scaling within Kubernetes through Cluster Autoscaler, Auto Scaling Groups,
and Horizontal Pod Autoscaler ensures that applications remain performant and
cost-effective by dynamically adjusting resources based on demand. Proper
configuration and monitoring of these components are crucial for maintaining an
efficient and reliable Kubernetes environment. By leveraging ASG, CA, and HPA
together, the Kubernetes infrastructure achieves both micro (pod-level) and
macro (node-level) scaling, ensuring that our applications are always backed by
the right amount of resources. This orchestration between different layers of
scaling mechanisms enables us to maintain high availability, performance, and
cost efficiency.
