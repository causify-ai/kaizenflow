# Comparison of AWS RDS Instance Types and Storage Performance

## Table of Contents

<!-- toc -->

- [Introduction](#introduction)
- [RDS Instance Types Evaluation](#rds-instance-types-evaluation)
    + [General Purpose Instances (e.g., `M5`, `T3`)](#general-purpose-instances-eg-m5-t3)
    + [Memory-Optimized Instances (e.g., `R5`, `R6g`)](#memory-optimized-instances-eg-r5-r6g)
    + [Compute-Optimized Instances (e.g., `C5`, `C6g`)](#compute-optimized-instances-eg-c5-c6g)
    + [Comparison Summary](#comparison-summary)
  * [Storage Types](#storage-types)
    + [`gp2` (General Purpose SSD)](#gp2-general-purpose-ssd)
    + [`gp3` (Next-Gen General Purpose SSD)](#gp3-next-gen-general-purpose-ssd)
    + [IO-optimized Storage](#io-optimized-storage)
    + [Comparison Summary](#comparison-summary-1)
  * [Performance Metrics](#performance-metrics)
- [Conclusion](#conclusion)

<!-- tocstop -->

## Introduction

This guide aims to conduct a comprehensive comparison of various AWS RDS
instance types and storage options. The focus is to understand the real-world
performance implications of different configurations, especially in terms of
instance types, and storage types like `gp2`, `gp3`, and `IO` options.

## RDS Instance Types Evaluation

#### General Purpose Instances (e.g., `M5`, `T3`)

- **Performance:** Balanced CPU and memory, suitable for moderate load
  applications.
- **Use Case:** Ideal for web applications, development, and test environments.

#### Memory-Optimized Instances (e.g., `R5`, `R6g`)

- **Performance:** Higher memory to CPU ratio. R6g instances leverage AWS
  Graviton processors for better price-performance.
- **Use Case:** Suitable for memory-intensive applications like high-performance
  databases.

#### Compute-Optimized Instances (e.g., `C5`, `C6g`)

- **Performance:** High CPU resources relative to memory. `C6g` instances are
  powered by AWS Graviton2 processors offering better compute performance.
- **Use Case:** Ideal for compute-intensive applications, like gaming servers,
  high-performance computing.

#### Comparison Summary

- **Memory-Optimized vs General Purpose:** Memory-optimized instances (like
  `R6g`) offer better performance for memory-heavy applications compared to
  general-purpose instances.
- **Compute-Optimized vs Memory-Optimized:** For CPU-intensive tasks,
  compute-optimized instances are preferable, whereas memory-optimized instances
  are better for memory-demanding applications.

### Storage Types

#### `gp2` (General Purpose SSD)

- **Performance:** Offers a balance of price and performance. Performance scales
  with volume size.
- **Use Case:** Suitable for a broad range of transactional workloads.

#### `gp3` (Next-Gen General Purpose SSD)

- **Performance:** Provides better performance at a lower cost than `gp2`.
  Offers customizable IOPS and throughput. Baseline of 3,000 IOPS and throughput
  of 125 MiB/s, scalable to 16,000 IOPS and 1,000 MiB/s
- **Use Case:** Ideal for applications requiring high-performance at a lower
  cost.

#### IO-optimized Storage

- **Performance:** Designed for high I/O operations per second (IOPS) and
  throughput. Offers provisioned IOPS (PIOPS) up to 64,000 IOPS
- **Use Case:** Essential for high-performance OLTP, big data, and applications
  with high IO requirements.

#### Comparison Summary

- **`gp3` vs `gp2`:** `gp3` offers better cost efficiency and performance
  customization compared to `gp2`.
- **IO-optimized vs General Purpose:** IO-optimized storage is superior for
  applications requiring high I/O throughput.

### Performance Metrics

- **IO x thousand:** Refers to the number of I/O operations per second (IOPS).
  Higher IOPS indicates better performance for read/write intensive operations.
  It represents the number of input/output operations per second (IOPS)
  multiplied by a factor of thousand.
- **Real-World Implication:** High IOPS (like in IO-optimized storage)
  translates to faster data retrieval and handling, crucial for databases with
  heavy read/write operations.
- **Impact on Database Performance:**
  - Database performance heavily relies on IO operations.
  - Higher IO rates typically lead to faster data retrieval and handling, which
    is crucial for databases with high transaction rates or large data sets.

## Conclusion

The choice of instance type and storage option in AWS RDS largely depends on the
specific application requirements. Memory-optimized instances like `r6g` are
ideal for high-performance databases, while `t4g` instances are more suited for
less demanding workloads. In terms of storage, `gp3` offers a good balance of
performance and cost, making it a suitable choice for a variety of applications.
Understanding AWS-specific metrics like IOPS is crucial in making informed
decisions about database configurations.
