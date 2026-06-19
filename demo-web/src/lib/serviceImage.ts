const PNG_IDS = new Set(["S-2", "S-44"]);

/** サービスID（S-2 〜 S-44）に対応する public 配下の画像URLを返す */
export function getServiceImageUrl(serviceId: string): string | null {
  if (!/^S-\d+$/.test(serviceId)) return null;
  const ext = PNG_IDS.has(serviceId) ? "png" : "jpg";
  return `/services/${serviceId}.${ext}`;
}
