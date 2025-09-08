import os
from os.path import join
from typing import Any
from typing import Dict

from app.drivers.tools.repair.AbstractRepairTool import AbstractRepairTool


class RepairLlama(AbstractRepairTool):
    def __init__(self) -> None:
        self.name = os.path.basename(__file__)[:-3].lower()
        super(RepairLlama, self).__init__(self.name)
        self.image_name = "andre15silva/repairllama:latest"
        self.hash_digest = (
            "sha256:84e6a0edc81b9edd08158c41a0ada00aa96ee9dbda699435c61f7f07669af513"
        )

    def invoke(
        self, bug_info: Dict[str, Any], task_config_info: Dict[str, Any]
    ) -> None:
        """
        self.dir_logs - directory to store logs
        self.dir_setup - directory to access setup scripts
        self.dir_expr - directory for experiment
        self.dir_output - directory to store artifacts/output
        """

        project_name = bug_info.get(self.key_project_name, "").strip()
        if project_name:
            base_path = join(self.dir_expr, "src", "src", project_name)
        else:
            base_path = join(self.dir_expr, "src")

        dir_java_src = join(base_path, bug_info[self.key_dir_source])
        dir_test_src = join(base_path, bug_info[self.key_dir_tests])
        dir_java_bin = join(base_path, bug_info[self.key_dir_class])
        dir_test_bin = join(base_path, bug_info[self.key_dir_test_class])
        patch_directory = join(self.dir_output, "patches")

        env = {}
        java_version = bug_info.get(self.key_java_version, 8)
        if int(java_version) <= 7:
            java_version = 8
        env["JAVA_HOME"] = f"/usr/lib/jvm/java-{java_version}-openjdk-amd64/"

        if bug_info[self.key_build_system] == "maven":
            # compile main + test classes so Flacoco can see target/test-classes
            mvn_skip = (
                "-Dcheckstyle.skip=true -Denforcer.skip=true -Dspotbugs.skip=true "
                "-Dforbiddenapis.skip=true -Dlicense.skip=true -DskipITs"
            )
            self.run_command(
                f"mvn -q {mvn_skip} -DskipTests=false -DfailIfNoTests=false test-compile",
                dir_path=base_path,
                env=env,
            )
            # put deps under target/dependency
            self.run_command(
                "mvn -q dependency:copy-dependencies -DoutputDirectory=target/dependency",
                dir_path=base_path,
                env=env,
            )

        # execute repair tool
        command = (
            f"python3.10 main.py "
            f"--dir_java_src {dir_java_src} "
            f"--dir_test_src {dir_test_src} "
            f"--dir_java_bin {dir_java_bin} "
            f"--dir_test_bin {dir_test_bin} "
            f"--patch_directory {patch_directory}"
        )

        timeout_h = str(task_config_info[self.key_timeout])
        repair_command = f"timeout -k 5m {timeout_h}h {command} "
        self.timestamp_log_start()
        status = self.run_command(repair_command, log_file_path=self.log_output_path, env=env)
        self.process_status(status)

        # Check if self.dir_setup exists in the container
        if not self.is_dir(self.dir_setup):
            self.emit_warning(f"[repairllama] setup directory does not exist: {self.dir_setup}")
        else:
            self.emit_normal(f"[repairllama] setup directory exists: {self.dir_setup}")

            # Run the verify_patches script if it exists
            verify_script = join(self.dir_setup, "verify_patches")
            if self.is_file(verify_script):
                self.emit_normal(f"[repairllama] running verifier script: {verify_script}")
                verify_cmd = f"bash {verify_script}"
                self.run_command(verify_cmd, log_file_path=self.log_output_path, env=env)
            else:
                self.emit_warning(f"[repairllama] verifier script not found at {verify_script}")

        self.timestamp_log_end()