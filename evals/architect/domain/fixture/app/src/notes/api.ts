import { getSessionToken } from "../session";

const BASE_URL = "https://api.jotter.example";

export type Note = {
  id: string;
  title: string;
  body: string;
  updated_at: string;
};

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${await getSessionToken()}`,
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(`${init.method ?? "GET"} ${path} failed with ${response.status}`);
  }
  return response;
}

export async function fetchNotes(): Promise<Note[]> {
  return (await request("/notes")).json();
}

export async function saveNote(id: string, title: string, body: string): Promise<Note> {
  const response = await request(`/notes/${id}`, {
    method: "PUT",
    body: JSON.stringify({ title, body }),
  });
  return response.json();
}

export async function deleteNote(id: string): Promise<void> {
  await request(`/notes/${id}`, { method: "DELETE" });
}
