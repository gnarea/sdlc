/** Read an environment variable that the workflow must set, refusing to guess a value it left out. */
export function readEnvironmentVariable(name) {
  const value = process.env[name];
  if (value === undefined || value === "") {
    throw new Error(`Environment variable ${name} must be set`);
  }
  return value;
}

/** Read an environment variable holding a pull request's number. */
export function readPullRequestNumber(name) {
  const value = readEnvironmentVariable(name);
  if (!/^[1-9]\d*$/.test(value)) {
    throw new Error(`Environment variable ${name} must be a pull request's number (got ${JSON.stringify(value)})`);
  }
  return Number(value);
}
