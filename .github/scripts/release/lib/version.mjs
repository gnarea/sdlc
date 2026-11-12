// Pre-releases and build metadata are left out, since the plugin is only released from `main`.
const VERSION_PATTERN = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;

export function isVersion(value) {
  return typeof value === "string" && VERSION_PATTERN.test(value);
}

/** Compare two versions, returning a negative number if the first is lower, zero if equal, and positive if higher. */
export function compareVersions(version1, version2) {
  const parts1 = parseVersion(version1);
  const parts2 = parseVersion(version2);
  const differingIndex = parts1.findIndex((part, index) => part !== parts2[index]);
  return differingIndex === -1 ? 0 : parts1[differingIndex] - parts2[differingIndex];
}

function parseVersion(version) {
  const match = VERSION_PATTERN.exec(version);
  if (match === null) {
    throw new Error(`Version must be "(major).(minor).(patch)" (got ${JSON.stringify(version)})`);
  }
  return match.slice(1).map(Number);
}
