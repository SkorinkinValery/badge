"use client";

import { useState } from "react";
import { authHeaders } from "@/lib/auth";
import { Button, Field, inputClass } from "@/components/ui";

interface Props {
  recordingId: string;
  currentScore: number | null;
  autoScore: number | null;
  currentVerdict: string | null;
  onSaved: () => void;
}

export default function ScoreCorrectionForm({
  recordingId,
  currentScore,
  autoScore,
  onSaved,
}: Props) {
  const [score, setScore] = useState<string>(currentScore != null ? String(currentScore) : "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    setError(null);
    setLoading(true);
    try {
      const resp = await fetch(`/api/recordings/${recordingId}/analysis`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ score: score === "" ? null : Number(score) }),
      });
      const body = await resp.json();
      if (!resp.ok) throw new Error(body?.detail ?? "Ошибка сохранения");
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {autoScore !== null && (
        <p className="text-[13px] text-muted">Исходная оценка: {autoScore}</p>
      )}
      {error && (
        <div
          role="alert"
          className="border border-danger/40 bg-danger/[0.08] px-[13px] py-[10px] text-[12.5px] text-danger"
        >
          {error}
        </div>
      )}
      <Field label="Оценка">
        <input
          className={inputClass}
          type="number"
          min={0}
          max={100}
          value={score}
          onChange={(e) => setScore(e.target.value)}
        />
      </Field>
      <div>
        <Button onClick={handleSave} disabled={loading}>
          {loading ? "Сохранение…" : "Сохранить"}
        </Button>
      </div>
    </div>
  );
}
