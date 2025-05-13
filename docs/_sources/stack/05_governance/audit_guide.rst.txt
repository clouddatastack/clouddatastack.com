Audit Guide
=================================

Here’s a practical guide to auditing and analyzing datasets, workloads, and costs within Databricks environment. This checklist helps understand data usage, performance, and cost management.

Inventory: What Data Assets Exist?
----------------------------------

**Show the top N largest tables in Databricks by size**

.. literalinclude:: code/databricks_audit.py
   :language: python
   :linenos:


Usage: Which datasets are regularly queried?
--------------------------------------------