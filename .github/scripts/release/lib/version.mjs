// Pre-releases and build metadata are left out, since the plugin is only released from `main`.
const VERSION_PATTERN = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;

export function isVersion(value) {
  return typeof value === "string" && VERSION_PATTERN.test(value);
}
