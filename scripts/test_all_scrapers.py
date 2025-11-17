import os
import subprocess
import glob

def main():
    # Step 1: Identify all scraper configurations
    config_dir = 'src/scrapers/configs'
    yaml_files = glob.glob(os.path.join(config_dir, '*.yaml'))
    scraper_names = [os.path.basename(f).replace('.yaml', '') for f in yaml_files]

    # Ensure logs directory exists
    logs_dir = 'logs'
    os.makedirs(logs_dir, exist_ok=True)

    tested_count = 0

    # Step 2-4: Test each scraper
    for scraper_name in scraper_names:
        print(f"Testing scraper: {scraper_name}")

        # Execute the test command
        process = subprocess.Popen(
            ['python', 'tests/platform_test_scrapers.py', '--scraper', scraper_name],
            env={'PYTHONPATH': os.getcwd()},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        returncode = process.returncode

        # Step 3: Handle errors and log output
        log_content = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        if returncode != 0:
            log_content += f"\nERROR: Command failed with return code {returncode}"

        log_file = os.path.join(logs_dir, f"{scraper_name}_test.log")
        with open(log_file, 'w') as f:
            f.write(log_content)

        tested_count += 1

    # Step 5: Print summary
    print(f"Summary: Tested {tested_count} scrapers.")

if __name__ == "__main__":
    main()