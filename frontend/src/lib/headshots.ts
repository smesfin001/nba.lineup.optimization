const HEADSHOT_URLS: Record<string, string> = {
  "Adou Thiero": "https://ui-avatars.com/api/?name=Adou+Thiero&background=4a3d63&color=ffffff&size=256&bold=true",
  "Austin Reaves": "https://cdn.nba.com/headshots/nba/latest/1040x760/1630559.png",
  "Bronny James": "https://cdn.nba.com/headshots/nba/latest/1040x760/1642353.png",
  "Chris Manon": "https://ui-avatars.com/api/?name=Chris+Manon&background=4a3d63&color=ffffff&size=256&bold=true",
  "Dalton Knecht": "https://ui-avatars.com/api/?name=Dalton+Knecht&background=4a3d63&color=ffffff&size=256&bold=true",
  "Deandre Ayton": "https://cdn.nba.com/headshots/nba/latest/1040x760/1629028.png",
  "Drew Timme": "https://ui-avatars.com/api/?name=Drew+Timme&background=4a3d63&color=ffffff&size=256&bold=true",
  "Jake LaRavia": "https://cdn.nba.com/headshots/nba/latest/1040x760/1631222.png",
  "Jarred Vanderbilt": "https://cdn.nba.com/headshots/nba/latest/1040x760/1629020.png",
  "Jaxson Hayes": "https://cdn.nba.com/headshots/nba/latest/1040x760/1629637.png",
  "Kobe Bufkin": "https://cdn.nba.com/headshots/nba/latest/1040x760/1641710.png",
  "LeBron James": "https://cdn.nba.com/headshots/nba/latest/1040x760/2544.png",
  "Luka Doncic": "https://cdn.nba.com/headshots/nba/latest/1040x760/1629029.png",
  "Luke Kennard": "https://cdn.nba.com/headshots/nba/latest/1040x760/1628379.png",
  "Marcus Smart": "https://cdn.nba.com/headshots/nba/latest/1040x760/203935.png",
  "Maxi Kleber": "https://cdn.nba.com/headshots/nba/latest/1040x760/1628467.png",
  "Nick Smith Jr.": "https://cdn.nba.com/headshots/nba/latest/1040x760/1641733.png",
  "Rui Hachimura": "https://cdn.nba.com/headshots/nba/latest/1040x760/1629060.png",
};

export function getHeadshotUrl(name: string): string | null {
  return HEADSHOT_URLS[name] ?? null;
}

export function getFallbackAvatarUrl(name: string): string {
  const encodedName = encodeURIComponent(name);
  return `https://ui-avatars.com/api/?name=${encodedName}&background=4a3d63&color=ffffff&size=256&bold=true`;
}
