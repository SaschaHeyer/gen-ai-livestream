import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import { addLog, getLogs } from "@/app/lib/logStore";

const UPLOAD_DIR = "/tmp/browser-use-uploads";

function sanitizeFileName(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, "_");
}

export async function POST(request: Request) {
  const formData = await request.formData();
  const note = String(formData.get("note") ?? "");
  const value = formData.get("file");
  if (!value || typeof value === "string") {
    return NextResponse.json({ error: "Missing file field" }, { status: 400 });
  }

  const fileName = sanitizeFileName(value.name || "upload.pdf");
  const bytes = Buffer.from(await value.arrayBuffer());
  const buffer = bytes;

  await fs.mkdir(UPLOAD_DIR, { recursive: true });
  const filePath = path.join(UPLOAD_DIR, fileName);
  await fs.writeFile(filePath, buffer);

  const entry = {
    timestamp: new Date().toISOString(),
    fileName,
    note,
  };
  addLog(entry);
  console.log(`[UPLOAD] Saved ${fileName} (${buffer.length} bytes) note="${note}"`);

  return NextResponse.json({ status: "ok", entry });
}

export async function GET() {
  return NextResponse.json({ logs: getLogs() });
}
