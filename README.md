# Evaluating Automated Program Repair on Time-Critical Hot fix Bugs

A fork of [Cerberus](https://github.com/nus-apr/cerberus) for evaluating APR tools on hot fix bugs from the [HotBugs.jar dataset](https://github.com/carolhanna01/HotBugs-dot-jar).

The original Cerberus documentation is preserved in [CERBERUS-README.md](CERBERUS-README.md).

---

## Requirements

- Python (this work used version 3.11)  
- Docker (installed and running)  
- Git  

Tool-specific requirements are handled automatically inside Docker containers.

---

## Setup

1. **Clone with submodules**
   ```bash
   git clone --recurse-submodules <repository-url>
   cd cerberus
   ```

2. **Create and activate a conda environment (recommended)**

   ```bash
   conda create -n cerberus python=3.11 -y
   conda activate cerberus
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Ensure Docker is running**

   ```bash
   docker --version
   sudo systemctl enable --now docker
   ```

   (Optional) To run without root:

   ```bash
   sudo usermod -aG docker $USER
   # log out and back in for the group change to take effect
   ```

5. **Activate cerberus**

   ```bash
   source activate
   ```

---

## Running Experiments

A single run can be launched as:

```bash
cerberus -task repair --tool nopol --benchmark bugsdotjar --bug-index 1159
```

- Replace `nopol` with any other supported tool:
  `repairllama`, `arja`, `jkali`, `cardumen`, `jmutrepair`, `jgenprog`.

- HotBugs.jar integration:
  67 bugs were added to the BugsDotJar benchmark.
  Out of these, 20 are runnable with the current configurations:

  ```
  1159, 1160, 1161, 1162, 1163, 1164, 1165, 1166,
  1169, 1172, 1173, 1174, 1175, 1176, 1179,
  1183, 1208, 1210, 1211, 1212
  ```

### Useful Options

- Enable debug logs:

  ```bash
  cerberus -task repair --tool nopol --benchmark bugsdotjar --bug-index 1164 --debug
  ```

- Run on a list of bugs:

  ```bash
  cerberus -task repair --tool jgenprog --benchmark bugsdotjar --bug-index-list=1159-1166
  ```

- Multiple runs for the same bug:

  ```bash
  cerberus -task repair --tool jgenprog --benchmark bugsdotjar --bug-index=1159 --runs=5 --debug
  ```

To view results, logs, and artifacts, check the folders: logs, results, summaries, output.
---

## Notes

All experiments were tested with Python 3.11.

