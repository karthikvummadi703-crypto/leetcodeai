import type { ConversationListItem } from "@/lib/api";

export type GroupKey = "Today" | "Yesterday" | "Previous 7 Days" | "Older";

export interface GroupedConversations {
  key: GroupKey;
  items: ConversationListItem[];
}

function startOfDay(date: Date): number {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function groupConversations(
  items: ConversationListItem[],
): GroupedConversations[] {
  const today = startOfDay(new Date());
  const yesterday = today - 86_400_000;
  const sevenDays = today - 6 * 86_400_000;

  const buckets: Record<GroupKey, ConversationListItem[]> = {
    Today: [],
    Yesterday: [],
    "Previous 7 Days": [],
    Older: [],
  };

  for (const item of items) {
    const ts = new Date(item.updated_at).getTime();
    if (Number.isNaN(ts)) {
      buckets["Older"].push(item);
    } else if (ts >= today) {
      buckets["Today"].push(item);
    } else if (ts >= yesterday) {
      buckets["Yesterday"].push(item);
    } else if (ts >= sevenDays) {
      buckets["Previous 7 Days"].push(item);
    } else {
      buckets["Older"].push(item);
    }
  }

  return (Object.keys(buckets) as GroupKey[])
    .map((key) => ({ key, items: buckets[key] }))
    .filter((group) => group.items.length > 0);
}
