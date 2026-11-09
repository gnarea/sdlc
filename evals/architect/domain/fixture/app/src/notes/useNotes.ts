import { useCallback, useEffect, useState } from "react";

import { deleteNote, fetchNotes, Note, saveNote } from "./api";

export function useNotes() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    fetchNotes().then(setNotes, setError);
  }, []);

  const save = useCallback(async (id: string, title: string, body: string) => {
    const saved = await saveNote(id, title, body);
    setNotes((current) => [saved, ...current.filter((note) => note.id !== id)]);
  }, []);

  const remove = useCallback(async (id: string) => {
    await deleteNote(id);
    setNotes((current) => current.filter((note) => note.id !== id));
  }, []);

  return { notes, error, save, remove };
}
