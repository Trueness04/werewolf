export type Me = {
  user_id: number;
  name: string;
  username?: string | null;
  coins: number;
  rank: number;
  xp: number;
};

export type FeedItem = {
  kind: string;
  id?: number;
  body?: string;
  created_at?: string;
  user_id?: number;
  user?: { user_id: number; name?: string };
};

export type Profile = {
  user_id: number;
  name: string;
  username?: string | null;
  bio?: string | null;
  rank: number;
  xp: number;
  coins: number;
  games_played: number;
  wins: number;
  icons?: { rank: number; title_fa: string }[];
};

export type RankRow = {
  place: number;
  name: string;
  rank: number;
  xp: number;
  coins: number;
  governor?: boolean;
  royal?: boolean;
  user_id?: number;
};

export type ShopItem = {
  id: string;
  title_fa: string;
  price: number;
  kind: string;
};

export type ChargePackage = {
  id: string;
  title_fa: string;
  price_toman: number;
  coins?: number;
};

export type ChargeOrder = {
  id: number;
  package_id: string;
  price_toman: number;
  coins: number;
  status: string;
  note?: string;
};
