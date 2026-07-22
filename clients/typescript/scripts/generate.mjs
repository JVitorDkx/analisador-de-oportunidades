import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const packageRoot = resolve(fileURLToPath(new URL('..', import.meta.url)));
const snapshotPath = resolve(packageRoot, '../../tests/api/snapshots/openapi.json');
const generatorPath = resolve(
  packageRoot,
  'node_modules/@hey-api/openapi-ts/bin/run.js',
);
const temporaryDirectory = mkdtempSync(join(tmpdir(), 'opportunity-openapi-'));
const compatibleSnapshotPath = join(temporaryDirectory, 'openapi.json');

const expandLocalDefinitions = (value, inheritedDefinitions, trail = []) => {
  if (Array.isArray(value)) {
    return value.map((item) => expandLocalDefinitions(item, inheritedDefinitions, trail));
  }
  if (value === null || typeof value !== 'object') {
    return value;
  }

  const definitions = value.$defs ?? inheritedDefinitions;
  if (typeof value.$ref === 'string' && value.$ref.startsWith('#/$defs/')) {
    const definitionName = value.$ref.slice('#/$defs/'.length);
    const definition = definitions?.[definitionName];
    if (!definition) {
      throw new Error(`Unresolved local OpenAPI definition: ${value.$ref}`);
    }
    if (trail.includes(definitionName)) {
      throw new Error(`Recursive local OpenAPI definition: ${value.$ref}`);
    }

    const expanded = expandLocalDefinitions(definition, definitions, [
      ...trail,
      definitionName,
    ]);
    const siblings = Object.fromEntries(
      Object.entries(value)
        .filter(([key]) => key !== '$ref' && key !== '$defs')
        .map(([key, item]) => [
          key,
          expandLocalDefinitions(item, definitions, trail),
        ]),
    );
    return Object.keys(siblings).length ? { allOf: [expanded], ...siblings } : expanded;
  }

  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => key !== '$defs')
      .map(([key, item]) => [
        key,
        expandLocalDefinitions(item, definitions, trail),
      ]),
  );
};

try {
  const frozenSnapshot = JSON.parse(readFileSync(snapshotPath, 'utf8'));
  const compatibleSnapshot = expandLocalDefinitions(frozenSnapshot);
  writeFileSync(compatibleSnapshotPath, `${JSON.stringify(compatibleSnapshot)}\n`);

  const generation = spawnSync(process.execPath, [generatorPath], {
    cwd: packageRoot,
    env: { ...process.env, SDK_INPUT_PATH: compatibleSnapshotPath },
    stdio: 'inherit',
  });
  if (generation.error) {
    throw generation.error;
  }
  process.exitCode = generation.status ?? 1;
} finally {
  rmSync(temporaryDirectory, { recursive: true, force: true });
}
