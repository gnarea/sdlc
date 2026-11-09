import * as SecureStore from "expo-secure-store";

export async function getSessionToken(): Promise<string | null> {
  return SecureStore.getItemAsync("session-token");
}
