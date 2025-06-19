import math
import re
import glob
from os.path import join
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from app.core.task.stats.RepairToolStats import RepairToolStats
from app.core.task.typing.DirectoryInfo import DirectoryInfo
from app.drivers.tools.repair.AbstractRepairTool import AbstractRepairTool


class AstorTool(AbstractRepairTool):

    astor_home = "/opt/astor"
    astor_version = "2.0.0"
    mode: Optional[str] = None

    # Define the key constants
    key_project_name = "project_name"
    key_java_version = "java_version"
    key_build_script = "build_script"
    key_build_system = "build_system"
    key_dependencies = "dependencies"
    key_timeout = "timeout"

    def __init__(self) -> None:
        super().__init__(self.name)
        self.image_name = "astor:2.0.0"

    def invoke(
        self, bug_info: Dict[str, Any], task_config_info: Dict[str, Any]
    ) -> None:
        """
        self.dir_logs - directory to store logs
        self.dir_setup - directory to access setup scripts
        self.dir_expr - directory for experiment
        self.dir_output - directory to store artifacts/output
        """
        self.emit_debug("=" * 80)
        self.emit_debug("STARTING ASTORTOOL INVOKE")
        self.emit_debug("=" * 80)
        
        # Log all input parameters
        self.emit_debug(f"Starting AstorTool.invoke with bug_info keys: {list(bug_info.keys())}")
        self.emit_debug(f"task_config_info keys: {list(task_config_info.keys())}")
        self.emit_debug(f"self.dir_expr: {self.dir_expr}")
        self.emit_debug(f"self.dir_setup: {self.dir_setup}")
        self.emit_debug(f"self.dir_output: {self.dir_output}")
        self.emit_debug(f"self.dir_logs: {self.dir_logs}")
        self.emit_debug(f"self.astor_home: {self.astor_home}")
        self.emit_debug(f"self.mode: {self.mode}")
        
        # Debug all bug_info values
        for key, value in bug_info.items():
            self.emit_debug(f"bug_info[{key}]: {value}")

        timeout_h = str(task_config_info[self.key_timeout])
        self.emit_debug(f"timeout_h: {timeout_h}")
        timeout_m = str(float(timeout_h) * 60)
        self.emit_debug(f"timeout_m: {timeout_m}")
        max_gen = 1000000

        # Check experiment directory structure
        self.emit_debug(f"Checking experiment directory structure:")
        if self.is_dir(self.dir_expr):
            contents = self.list_dir(self.dir_expr)
            self.emit_debug(f"Contents of {self.dir_expr}: {contents}")
            
            # Check src subdirectory
            src_dir = join(self.dir_expr, "src")
            if self.is_dir(src_dir):
                src_contents = self.list_dir(src_dir)
                self.emit_debug(f"Contents of {src_dir}: {src_contents}")
                
                # Check src/src subdirectory
                src_src_dir = join(src_dir, "src")
                if self.is_dir(src_src_dir):
                    src_src_contents = self.list_dir(src_src_dir)
                    self.emit_debug(f"Contents of {src_src_dir}: {src_src_contents}")
            else:
                self.emit_debug(f"src directory not found: {src_dir}")
        else:
            self.emit_debug(f"Experiment directory not found: {self.dir_expr}")

        # Get paths - handle the nested src/src structure in bugsdotjar
        base_src_path = join(self.dir_expr, "src", "src")
        self.emit_debug(f"Base source path: {base_src_path}")
        
        # Determine sub-project from bug_info - CRITICAL FIX
        project_name = bug_info.get(self.key_project_name, "")
        if not project_name:
            project_name = bug_info.get("project_name", "")
        self.emit_debug(f"Raw project name: '{project_name}'")
        
        # Clean up project name and determine sub-project path
        if project_name:
            if project_name.endswith("/"):
                project_name = project_name[:-1]
            sub_project_path = join(base_src_path, project_name)
            self.emit_debug(f"Using project_name from bug_info: {project_name}")
        else:
            # Fallback - look for sub-projects
            sub_project_path = base_src_path
            if self.is_dir(base_src_path):
                contents = self.list_dir(base_src_path)
                self.emit_debug(f"Looking for sub-projects in {base_src_path}: {contents}")
                for item in contents:
                    item_path = join(base_src_path, item)
                    if self.is_dir(item_path) and self.is_file(join(item_path, "pom.xml")):
                        self.emit_debug(f"Found potential sub-project: {item}")
                        if "java" in item.lower():
                            sub_project_path = item_path
                            project_name = item
                            break

        self.emit_debug(f"Final sub-project path: {sub_project_path}")
        self.emit_debug(f"Final project name: {project_name}")

        # Verify sub-project structure
        if self.is_dir(sub_project_path):
            sub_contents = self.list_dir(sub_project_path)
            self.emit_debug(f"Sub-project contents: {sub_contents}")
            
            pom_path = join(sub_project_path, "pom.xml")
            if self.is_file(pom_path):
                self.emit_debug(f"Found pom.xml at: {pom_path}")
            else:
                self.emit_debug(f"WARNING: No pom.xml found at: {pom_path}")
        else:
            self.emit_debug(f"ERROR: Sub-project path does not exist: {sub_project_path}")

        # Set up paths based on Maven structure
        dir_java_src = join(sub_project_path, "src", "main", "java")
        dir_test_src = join(sub_project_path, "src", "test", "java") 
        dir_java_bin = join(sub_project_path, "target", "classes")
        dir_test_bin = join(sub_project_path, "target", "test-classes")
        
        self.emit_debug(f"Maven structure paths:")
        self.emit_debug(f"  dir_java_src: {dir_java_src}")
        self.emit_debug(f"  dir_test_src: {dir_test_src}")
        self.emit_debug(f"  dir_java_bin: {dir_java_bin}")
        self.emit_debug(f"  dir_test_bin: {dir_test_bin}")

        # Check if paths exist
        self.emit_debug(f"Path existence check:")
        self.emit_debug(f"  dir_java_src exists: {self.is_dir(dir_java_src)}")
        self.emit_debug(f"  dir_test_src exists: {self.is_dir(dir_test_src)}")
        self.emit_debug(f"  dir_java_bin exists: {self.is_dir(dir_java_bin)}")
        self.emit_debug(f"  dir_test_bin exists: {self.is_dir(dir_test_bin)}")

        # Check bin directory contents
        if self.is_dir(dir_java_bin):
            java_bin_contents = self.list_dir(dir_java_bin)
            self.emit_debug(f"Java bin directory contents: {java_bin_contents}")
        if self.is_dir(dir_test_bin):
            test_bin_contents = self.list_dir(dir_test_bin)
            self.emit_debug(f"Test bin directory contents: {test_bin_contents}")

        # Set up Java environment
        env = {}
        java_version = bug_info.get(self.key_java_version, 8)
        self.emit_debug(f"java_version (raw): {java_version}")
        if int(java_version) <= 7:
            java_version = 8
            self.emit_debug("java_version <= 7, setting to 8")
        
        # Try multiple Java paths
        java_paths = [
            f"/usr/lib/jvm/java-{java_version}-openjdk-amd64/",
            f"/usr/lib/jvm/zulu-{java_version}-amd64/",
            f"/usr/lib/jvm/java-{java_version}-openjdk/",
            f"/usr/lib/jvm/default-java/"
        ]
        
        java_home = None
        for java_path in java_paths:
            if self.is_dir(java_path):
                java_home = java_path
                self.emit_debug(f"Found Java at: {java_path}")
                break
            
        if java_home:
            env["JAVA_HOME"] = java_home
            self.emit_debug(f"JAVA_HOME set to: {env['JAVA_HOME']}")
        else:
            self.emit_debug(f"WARNING: No Java installation found")

        # Run build script
        build_script = bug_info.get(self.key_build_script)
        self.emit_debug(f"Build script: {build_script}")
        self.emit_debug(f"Setup directory: {self.dir_setup}")
        
        if build_script and self.is_file(join(self.dir_setup, build_script)):
            self.emit_debug(f"Running build script: {build_script} in {self.dir_setup}")
            build_result = self.run_command(
                f"bash {build_script}",
                dir_path=self.dir_setup,
                env=env,
            )
            self.emit_debug(f"Build script result: {build_result}")
        else:
            self.emit_debug(f"Build script not found or not specified")

        # CRITICAL DEPENDENCY HANDLING FIX
        self.emit_debug("=" * 40)
        self.emit_debug("DEPENDENCY HANDLING")
        self.emit_debug("=" * 40)
        
        # Get initial dependencies from bug_info
        initial_deps = bug_info.get(self.key_dependencies, [])
        self.emit_debug(f"Initial dependencies from bug_info: {initial_deps}")
        
        list_deps = []
        for dep in initial_deps:
            if dep.startswith("/"):
                list_deps.append(dep)
            else:
                list_deps.append(join(self.dir_expr, dep))
        
        self.emit_debug(f"Processed initial dependencies: {list_deps}")
        
        # # Add JUnit and Hamcrest from Astor
        # junit_hamcrest_deps = [
        #     join(self.astor_home, "external", "lib", "hamcrest-core-1.3.jar"),
        #     join(self.astor_home, "external", "lib", "junit-4.12.jar"),
        # ]
        
        # for dep in junit_hamcrest_deps:
        #     if self.is_file(dep):
        #         list_deps.append(dep)
        #         self.emit_debug(f"Added Astor dependency: {dep}")
        #     else:
        #         self.emit_debug(f"Astor dependency not found: {dep}")
        # ------------------------------------------------------------------
        # 1️⃣  Always inject Astor’s own *latest* junit 4.12 & hamcrest-core 1.3
        #     (they live in  /opt/astor/lib  in the astor:2.0.0 image)
        #     They must be *first* on the class-path so they shadow Flink’s
        #     older junit-4.11, otherwise Flacoco’s forked JVM crashes.
        # ------------------------------------------------------------------
        astor_lib_dir = join(self.astor_home, "lib")
        for jar in ("junit-4.12.jar", "hamcrest-core-1.3.jar"):
            jar_path = join(astor_lib_dir, jar)
            if self.is_file(jar_path):
                list_deps.insert(0, jar_path)          # put at front
                self.emit_debug(f"Injected Astor lib: {jar_path}")
            else:
                self.emit_debug(f"Astor lib NOT found: {jar_path}")

        # later, before deduplication, drop any junit-4.11 that slipped in
        
        # Handle Maven dependencies - CRITICAL FIX
        build_system = bug_info.get(self.key_build_system, "")
        self.emit_debug(f"Build system: {build_system}")
        
        if build_system.lower() == "maven":
            self.emit_debug("Build system is Maven, handling Maven dependencies")
            
            # # First run parent/root maven install to ensure all modules are available
            # root_maven_path = join(self.dir_expr, "src", "src")
            # if self.is_file(join(root_maven_path, "pom.xml")):
            #     self.emit_debug(f"Running maven install on root project at {root_maven_path}")
            #     root_install_result = self.run_command(
            #         "mvn install -DskipTests -DskipUTs=true -DskipITs=true -Drat.skip=true -q",
            #         dir_path=root_maven_path,
            #         env=env,
            #     )
            #     self.emit_debug(f"Root maven install result: {root_install_result}")
            # --- we skip the parent build entirely (Apache-RAT fails there) ---
            root_maven_path = join(self.dir_expr, "src", "src")
            self.emit_debug(f"SKIPPING root mvn install in {root_maven_path} to avoid RAT check")
            
            # Run mvn dependency:copy-dependencies in the sub-project
            self.emit_debug(f"Running mvn dependency:copy-dependencies in {sub_project_path}")
            dep_result = self.run_command(
                "mvn dependency:copy-dependencies -DskipTests -q",
                dir_path=sub_project_path,
                env=env,
            )
            self.emit_debug(f"Maven dependency copy result: {dep_result}")
            
            # Look for Maven dependencies in multiple locations
            maven_dep_paths = [
                join(sub_project_path, "target", "dependency"),
                join(sub_project_path, "target"),
                join(root_maven_path, "target", "dependency"),
            ]
            
            for dep_path in maven_dep_paths:
                self.emit_debug(f"Checking for dependencies in: {dep_path}")
                if self.is_dir(dep_path):
                    dep_contents = self.list_dir(dep_path)
                    self.emit_debug(f"Contents of {dep_path}: {dep_contents}")
                    
                    jar_files = [f for f in dep_contents if f.endswith('.jar')]
                    self.emit_debug(f"JAR files found: {jar_files}")
                    
                    for jar_file in jar_files:
                        jar_path = join(dep_path, jar_file)
                        if self.is_file(jar_path) and jar_path not in list_deps:
                            list_deps.append(jar_path)
                            self.emit_debug(f"Added Maven dependency: {jar_path}")
                else:
                    self.emit_debug(f"Dependency path does not exist: {dep_path}")
            
            # Also add any built JARs from the project itself
            project_jars = [
                join(sub_project_path, "target", f"flink-{project_name}-0.7-incubating-SNAPSHOT.jar"),
                join(sub_project_path, "target", f"{project_name}-0.7-incubating-SNAPSHOT.jar"),
            ]
            
            for jar_path in project_jars:
                if self.is_file(jar_path) and jar_path not in list_deps:
                    list_deps.append(jar_path)
                    self.emit_debug(f"Added project JAR: {jar_path}")
            
            # Add core Flink modules that might be needed
            flink_core_paths = [
                join(root_maven_path, "flink-core", "target", "classes"),
                join(root_maven_path, "flink-core", "target", "flink-core-0.7-incubating-SNAPSHOT.jar"),
            ]
            
            for core_path in flink_core_paths:
                if (self.is_dir(core_path) or self.is_file(core_path)) and core_path not in list_deps:
                    list_deps.append(core_path)
                    self.emit_debug(f"Added Flink core dependency: {core_path}")
        
        # Add the binary directories themselves to classpath
        if self.is_dir(dir_java_bin):
            list_deps.append(dir_java_bin)
            self.emit_debug(f"Added java bin directory to classpath: {dir_java_bin}")
        
        if self.is_dir(dir_test_bin):
            list_deps.append(dir_test_bin)
            self.emit_debug(f"Added test bin directory to classpath: {dir_test_bin}")
        
        # # Remove duplicates while preserving order
        # unique_deps = []
        # for dep in list_deps:
        #     if dep not in unique_deps:
        #         unique_deps.append(dep)
        # list_deps = unique_deps
        # Remove duplicates while preserving order and filter out junit-4.11
        unique_deps = []
        for dep in list_deps:
            if dep.endswith("junit-4.11.jar"):
                self.emit_debug(f"Filtered conflicting JUnit: {dep}")
                continue
            if dep not in unique_deps:
                unique_deps.append(dep)
        list_deps = unique_deps
        
        self.emit_debug(f"Final dependencies list ({len(list_deps)} items):")
        for i, dep in enumerate(list_deps):
            exists = self.is_file(dep) or self.is_dir(dep)
            dep_type = "FILE" if self.is_file(dep) else "DIR" if self.is_dir(dep) else "MISSING"
            self.emit_debug(f"  {i+1}. {dep} ({dep_type})")
        
        list_deps_str = ":".join(list_deps)
        self.emit_debug(f"Dependencies string length: {len(list_deps_str)}")

        # Generate Astor repair command
        self.emit_debug("=" * 40)
        self.emit_debug("GENERATING ASTOR COMMAND")
        self.emit_debug("=" * 40)
        
        self.timestamp_log_start()
        
        # CRITICAL FIX: Use relative paths for bin folders to avoid Astor path concatenation bug
        # Astor has a bug where it concatenates the location path with absolute bin paths
        # The error shows: /experiment/.../src/src/flink-java/experiment/.../src/src/flink-java/target/classes
        # This happens because Astor concatenates location + binjavafolder when binjavafolder is absolute
        rel_java_bin = "target/classes"
        rel_test_bin = "target/test-classes"
        
        self.emit_debug(f"Using relative bin paths to avoid Astor path concatenation bug:")
        self.emit_debug(f"  Relative java bin: {rel_java_bin}")
        self.emit_debug(f"  Relative test bin: {rel_test_bin}")
        self.emit_debug(f"  These will be resolved relative to location: {sub_project_path}")
        
        # Verify the actual paths exist before proceeding
        actual_java_bin = join(sub_project_path, rel_java_bin)
        actual_test_bin = join(sub_project_path, rel_test_bin)
        self.emit_debug(f"  Actual java bin path: {actual_java_bin} (exists: {self.is_dir(actual_java_bin)})")
        self.emit_debug(f"  Actual test bin path: {actual_test_bin} (exists: {self.is_dir(actual_test_bin)})")
        
        # Ensure the target directories exist - if not, we need to compile first
        if not self.is_dir(actual_java_bin) or not self.is_dir(actual_test_bin):
            self.emit_debug("Target directories don't exist, running Maven compile")
            compile_result = self.run_command(
                "mvn compile test-compile -DskipTests -q",
                dir_path=sub_project_path,
                env=env,
            )
            self.emit_debug(f"Maven compile result: {compile_result}")
            
            # Check again after compilation
            self.emit_debug(f"After compilation - java bin exists: {self.is_dir(actual_java_bin)}")
            self.emit_debug(f"After compilation - test bin exists: {self.is_dir(actual_test_bin)}")
        tmax1_ms = 300_000

        repair_command = (
            f"timeout -k 5m {timeout_h}h "
            f"java -cp target/astor-{self.astor_version}-jar-with-dependencies.jar "
            f"fr.inria.main.evolution.AstorMain "
            f"-classestoinstrument org.apache.flink.api.java.typeutils.TypeExtractor "
            f"-faultlocalization "
            f"fr.inria.astor.core.faultlocalization.gzoltar.GZoltarFaultLocalization "
            # f"-skipfaultlocalization "
            f"-mode {self.mode} "
            f"-javacompliancelevel 7 "
            f"-alternativecompliancelevel 7 "
            f"-tmax1 {tmax1_ms} "
            f"-tmax2 900000 "
            + (f"-loglevel DEBUG " if self.is_debug else "-loglevel INFO ")
            + f"-srcjavafolder {dir_java_src} "
            f"-srctestfolder {dir_test_src} "
            f"-binjavafolder {rel_java_bin} "
            f"-bintestfolder {rel_test_bin} "
            f"-location {sub_project_path} "
            f"-dependencies {list_deps_str} "
            f"-maxgen {max_gen} "
            f"-maxtime {int(math.ceil(float(timeout_m)))} "
            f"-failing org.apache.flink.api.java.type.extractor.TypeExtractorTest "
            f"-stopfirst false "
        )
        
        self.emit_debug(f"Complete repair command:")
        self.emit_debug(repair_command)
        self.emit_debug(f"Expected bin resolution:")
        self.emit_debug(f"  {sub_project_path}/{rel_java_bin} = {actual_java_bin}")
        self.emit_debug(f"  {sub_project_path}/{rel_test_bin} = {actual_test_bin}")
        
        # Check Astor jar existence
        astor_jar = f"target/astor-{self.astor_version}-jar-with-dependencies.jar"
        astor_jar_path = join(self.astor_home, astor_jar)
        self.emit_debug(f"Checking Astor jar: {astor_jar_path}")
        self.emit_debug(f"Astor jar exists: {self.is_file(astor_jar_path)}")
        
        # Check Astor home directory
        if self.is_dir(self.astor_home):
            astor_contents = self.list_dir(self.astor_home)
            self.emit_debug(f"Contents of Astor home ({self.astor_home}): {astor_contents}")
            
            target_dir = join(self.astor_home, "target")
            if self.is_dir(target_dir):
                target_contents = self.list_dir(target_dir)
                self.emit_debug(f"Contents of Astor target: {target_contents}")
        
        # Final environment check
        self.emit_debug(f"Final environment variables:")
        for key, value in env.items():
            self.emit_debug(f"  {key}={value}")
        
        self.emit_debug(f"Current working directory for Astor: {self.astor_home}")
        
        # Run Astor repair command
        self.emit_debug("=" * 40)
        self.emit_debug("RUNNING ASTOR")
        self.emit_debug("=" * 40)

        status = self.run_command(
            repair_command, 
            dir_path=self.astor_home,  # Use 'dir_path' instead of 'cwd'
            env=env
        )

        self.emit_debug(f"Astor execution finished with status: {status}")
        self.process_status(status)

        self.timestamp_log_end()
        self.emit_highlight("log file: {0}".format(self.log_output_path))
        
        # Log final output contents
        if self.is_file(self.log_output_path):
            self.emit_debug(f"Log file created successfully: {self.log_output_path}")
        else:
            self.emit_debug(f"Warning: Log file not found: {self.log_output_path}")
        
        self.emit_debug("=" * 80)
        self.emit_debug("ASTORTOOL INVOKE COMPLETED")
        self.emit_debug("=" * 80)

    def save_artifacts(self, dir_info: Dict[str, str]) -> None:
        """
        Save useful artifacts from the repair execution
        output folder -> self.dir_output
        logs folder -> self.dir_logs
        The parent method should be invoked at last to archive the results
        """
        list_artifact_dirs = [
            self.astor_home + "/" + x for x in ["diffSolutions", "output_astor"]
        ]
        for d in list_artifact_dirs:
            copy_command = f"cp -rf {d} {self.dir_output}"
            self.run_command(copy_command)
        super(AstorTool, self).save_artifacts(dir_info)

    def analyse_output(
        self, dir_info: DirectoryInfo, bug_id: str, fail_list: List[str]
    ) -> RepairToolStats:
        """
        analyse tool output and collect information
        output of the tool is logged at self.log_output_path
        information required to be extracted are:

            self.stats.patches_stats.non_compilable
            self.stats.patches_stats.plausible
            self.stats.patches_stats.size
            self.stats.patches_stats.enumerations
            self.stats.patches_stats.generated

            self.stats.time_stats.total_validation
            self.stats.time_stats.total_build
            self.stats.time_stats.timestamp_compilation
            self.stats.time_stats.timestamp_validation
            self.stats.time_stats.timestamp_plausible
        """
        self.emit_normal("reading output")

        count_plausible = 0
        count_enumerations = 0
        count_compilable = 0

        # count number of patch files
        list_output_dir = self.list_dir(self.dir_output)
        self.stats.patch_stats.generated = len(
            [name for name in list_output_dir if ".patch" in name]
        )

        # extract information from output log
        if not self.log_output_path or not self.is_file(self.log_output_path):
            self.emit_warning("no output log file found")
            return self.stats

        self.emit_highlight(f"output log file: {self.log_output_path}")

        if self.is_file(self.log_output_path):
            log_lines = self.read_file(self.log_output_path, encoding="iso-8859-1")
            self.stats.time_stats.timestamp_start = log_lines[0].replace("\n", "")
            self.stats.time_stats.timestamp_end = log_lines[-1].replace("\n", "")
            for line in log_lines:
                if "child compiles" in line.lower():
                    count_compilable += 1
                    identifier = re.search(r"id (.*)", line)
                    if not identifier:
                        self.emit_warning("No Id found")
                        continue
                    child_id = int(str(identifier.group(1)).strip())
                    if child_id > count_enumerations:
                        count_enumerations = child_id
                elif "found solution," in line.lower():
                    count_plausible += 1

        self.stats.patch_stats.generated = len(
            [
                x
                for x in self.list_dir(join(self.astor_home, "diffSolutions"))
                if ".diff" in x
            ]
        )
        self.stats.patch_stats.enumerations = count_enumerations
        self.stats.patch_stats.plausible = count_plausible
        self.stats.patch_stats.non_compilable = count_enumerations - count_compilable

        return self.stats
