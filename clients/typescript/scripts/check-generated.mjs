import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const packageRoot = resolve(fileURLToPath(new URL('..', import.meta.url)));
const committedOutput = join(packageRoot, 'src', 'generated');
const temporaryOutput = mkdtempSync(join(tmpdir(), 'opportunity-sdk-'));

const listFiles = (root) => {
  const files = [];
  const visit = (directory) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = join(directory, entry.name);
      if (entry.isDirectory()) {
        visit(path);
      } else if (entry.isFile()) {
        files.push(relative(root, path).replaceAll('\\', '/'));
      }
    }
  };
  visit(root);
  return files.sort();
};

try {
  const generation = spawnSync(process.execPath, ['scripts/generate.mjs'], {
    cwd: packageRoot,
    env: { ...process.env, SDK_OUTPUT_PATH: temporaryOutput },
    stdio: 'inherit',
  });
  if (generation.error) {
    throw generation.error;
  }
  if (generation.status !== 0) {
    process.exitCode = generation.status ?? 1;
  } else {
    const committedFiles = listFiles(committedOutput);
    const generatedFiles = listFiles(temporaryOutput);
    const differences = [];

    if (committedFiles.join('\n') !== generatedFiles.join('\n')) {
      differences.push('generated file list differs');
    }
    for (const file of committedFiles.filter((item) => generatedFiles.includes(item))) {
      const committed = readFileSync(join(committedOutput, file));
      const generated = readFileSync(join(temporaryOutput, file));
      if (!committed.equals(generated)) {
        differences.push(file);
      }
    }

    if (differences.length) {
      console.error(
        `Generated SDK is stale (${differences.map((item) => basename(item)).join(', ')}).`,
      );
      process.exitCode = 1;
    } else {
      console.log('Generated SDK matches the frozen OpenAPI snapshot.');
    }
  }
} finally {
  if (statSync(temporaryOutput).isDirectory()) {
    rmSync(temporaryOutput, { recursive: true, force: true });
  }
}
