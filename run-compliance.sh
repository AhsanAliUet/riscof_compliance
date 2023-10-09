
rm -rf riscof_work/
rm -rf verilator_work/

set -e   # exit immediately if got error (s), helpful for CI/CD Pipelines

riscof -v debug run --config=config.ini \
           --suite=riscv-arch-test/riscv-test-suite/rv32i_m/I \
           --env=riscv-arch-test/riscv-test-suite/env \
           --no-browser