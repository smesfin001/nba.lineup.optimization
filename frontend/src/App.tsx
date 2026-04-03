import { type FormEvent, type ReactNode, startTransition, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, ChevronDown, LoaderCircle, Shield, Sparkles, Waves } from "lucide-react";

import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Progress } from "./components/ui/progress";
import { Separator } from "./components/ui/separator";
import { Skeleton } from "./components/ui/skeleton";
import { getFallbackAvatarUrl, getHeadshotUrl } from "./lib/headshots";
import { cn } from "./lib/utils";

type QueryConstraints = {
  must_include: number[];
  must_exclude: number[];
  max_non_shooters?: number;
  min_size_score?: number;
  min_trust?: number;
};

type PlayerListItem = {
  player_id: number;
  name: string;
  position: string;
};

type IntentWeights = {
  defense: number;
  spacing: number;
  shooting: number;
  size: number;
  playmaking: number;
};

type PlayerCard = {
  player_id: number;
  name: string;
  position: string;
  height_inches: number | null;
  minutes_per_game: number | null;
  games_played: number | null;
  three_pct: number | null;
  dbpm: number | null;
};

type LineupInsight = {
  label: string;
  value: string;
  tone: string;
};

type Recommendation = {
  rank: number;
  player_ids: number[];
  player_names: string[];
  players: PlayerCard[];
  score: number;
  component_scores: Record<string, number>;
  trust_score: number;
  historical_seen: boolean;
  lineup_metadata: {
    minutes_played: number;
    net_rating: number | null;
    offensive_rating: number | null;
    defensive_rating: number | null;
    rotation_score: number;
  };
  lineup_insights: LineupInsight[];
  reasoning: string;
};

type OptimizeResponse = {
  recommendations: Recommendation[];
  parsed_intent: {
    weights: IntentWeights;
    constraints: QueryConstraints;
  };
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const SUGGESTED_QUERIES = [
  "Need defense and shooting around LeBron",
  "Best spacing group with Luka handling the ball",
  "Most trustworthy closing unit against big wings",
  "Need size without sacrificing playmaking",
];

const metricLabels: Record<string, string> = {
  defense: "Defense",
  spacing: "Spacing",
  shooting: "Shooting",
  size: "Size",
  playmaking: "Playmaking",
  weighted_score: "Feature fit",
  historical_score: "Historical trust",
  final_score: "Final blend",
};

const initialConstraints: QueryConstraints = {
  must_include: [],
  must_exclude: [],
};

function App() {
  const [query, setQuery] = useState(SUGGESTED_QUERIES[0]);
  const [constraints, setConstraints] = useState<QueryConstraints>(initialConstraints);
  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [loadingPlayers, setLoadingPlayers] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<OptimizeResponse | null>(null);
  const resultsRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const abortController = new AbortController();

    async function loadPlayers() {
      try {
        const rosterResponse = await fetch(`${API_BASE_URL}/players`, { signal: abortController.signal });
        if (!rosterResponse.ok) {
          throw new Error("Unable to load Lakers roster.");
        }
        const payload = (await rosterResponse.json()) as { players: PlayerListItem[] };
        startTransition(() => {
          setPlayers(payload.players);
        });
      } catch (loadError) {
        if (!(loadError instanceof DOMException && loadError.name === "AbortError")) {
          setError("Roster options could not be loaded. You can still submit free-text queries.");
        }
      } finally {
        setLoadingPlayers(false);
      }
    }

    loadPlayers();
    return () => abortController.abort();
  }, []);

  useEffect(() => {
    if (!response || loading || error) {
      return;
    }
    resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [response, loading, error]);

  const selectedIncludeNames = useMemo(
    () => players.filter((player) => constraints.must_include.includes(player.player_id)).map((player) => player.name),
    [constraints.must_include, players],
  );
  const selectedExcludeNames = useMemo(
    () => players.filter((player) => constraints.must_exclude.includes(player.player_id)).map((player) => player.name),
    [constraints.must_exclude, players],
  );

  async function submitQuery(nextQuery?: string) {
    const outgoingQuery = (nextQuery ?? query).trim();
    if (!outgoingQuery) {
      setError("Enter a lineup question before searching.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const optimizeResponse = await fetch(`${API_BASE_URL}/optimize-lineup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: outgoingQuery,
          constraints,
          limit: 3,
        }),
      });
      if (!optimizeResponse.ok) {
        throw new Error("The lineup engine did not return a valid response.");
      }
      const payload = (await optimizeResponse.json()) as OptimizeResponse;
      startTransition(() => {
        setQuery(outgoingQuery);
        setResponse(payload);
      });
    } catch {
      setError("Unable to fetch lineup recommendations. Verify the FastAPI server is running.");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuery();
  }

  function togglePlayer(listKey: "must_include" | "must_exclude", playerId: number) {
    setConstraints((current) => {
      const currentList = current[listKey];
      const nextList = currentList.includes(playerId)
        ? currentList.filter((id) => id !== playerId)
        : [...currentList, playerId];
      const opposingKey = listKey === "must_include" ? "must_exclude" : "must_include";
      return {
        ...current,
        [listKey]: nextList,
        [opposingKey]: current[opposingKey].filter((id) => id !== playerId),
      };
    });
  }

  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-noise opacity-90" />
      <div className="pointer-events-none absolute left-1/2 top-0 h-[32rem] w-[32rem] -translate-x-1/2 rounded-full bg-[#724ad4]/30 blur-[120px]" />
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 pb-12 pt-6 sm:px-6 lg:px-8">
        <header className="flex items-center justify-between rounded-full border border-white/10 bg-white/5 px-5 py-3 backdrop-blur-xl">
          <div>
            <p className="font-display text-sm font-semibold uppercase tracking-[0.28em] text-gold">Lakers Lab</p>
            <p className="text-sm text-white/60">Matchup-ready lineup answers for the current roster</p>
          </div>
          <Badge variant="subtle" className="hidden sm:inline-flex">
            Local MVP
          </Badge>
        </header>

        <section className="relative mx-auto mt-12 flex w-full max-w-5xl flex-col items-center text-center">
          <h1 className="font-display text-5xl font-extrabold leading-[0.95] text-white sm:text-6xl lg:text-7xl">
            Build the
            <span className="bg-gradient-to-r from-gold via-[#ffe39f] to-lilac bg-clip-text text-transparent"> right five</span>
            <br />
            before tip-off.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-white/70">
            Ask for the best unit for spacing, point-of-attack defense, closing minutes, or a specific matchup. You
            will get three ranked answers with the players first and the rationale second.
          </p>

          <form onSubmit={onSubmit} className="mt-10 w-full">
            <div className="rounded-[32px] border border-white/12 bg-cream p-3 shadow-[0_24px_80px_rgba(7,5,18,0.28)]">
              <div className="flex flex-col gap-3 lg:flex-row">
                <div className="flex flex-1 items-center gap-3 rounded-[24px] bg-white px-4 py-2">
                  <Sparkles className="h-5 w-5 text-court/40" />
                  <Input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    className="h-14 border-none bg-transparent px-0 text-lg text-ink shadow-none focus:ring-0"
                    placeholder="Ask about defense, shooting, size, or a closing group..."
                  />
                </div>
                <Button className="h-16 rounded-[24px] px-7 text-base" type="submit" disabled={loading}>
                  {loading ? <LoaderCircle className="mr-2 h-5 w-5 animate-spin" /> : <ArrowRight className="mr-2 h-5 w-5" />}
                  Find lineups
                </Button>
              </div>
            </div>
          </form>

          <div className="mt-6 flex flex-wrap justify-center gap-3">
            {SUGGESTED_QUERIES.map((suggestion) => (
              <Button
                key={suggestion}
                variant="chip"
                className="rounded-full px-5 py-3"
                onClick={() => {
                  setQuery(suggestion);
                  void submitQuery(suggestion);
                }}
              >
                {suggestion}
              </Button>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-center gap-3 text-sm text-white/58">
            <button
              type="button"
              onClick={() => setShowFilters((current) => !current)}
              className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/6 px-4 py-2 font-semibold text-white transition hover:bg-white/10"
            >
              Advanced filters
              <ChevronDown className={cn("h-4 w-4 transition", showFilters && "rotate-180")} />
            </button>
            {selectedIncludeNames.length > 0 && <Badge variant="subtle">Include: {selectedIncludeNames.join(", ")}</Badge>}
            {selectedExcludeNames.length > 0 && <Badge variant="subtle">Exclude: {selectedExcludeNames.join(", ")}</Badge>}
          </div>

          {showFilters && (
            <Card className="mt-6 w-full max-w-5xl text-left">
              <CardHeader className="pb-4">
                <CardTitle>Rotation Filters</CardTitle>
                <CardDescription>
                  Fine-tune the request with must-include and matchup guardrails while keeping the home screen clean.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
                <div className="grid gap-5">
                  <FilterGroup
                    title="Must include"
                    description="Pick players that must appear in every proposed lineup."
                    players={players}
                    selected={constraints.must_include}
                    loading={loadingPlayers}
                    onToggle={(playerId) => togglePlayer("must_include", playerId)}
                  />
                  <FilterGroup
                    title="Must exclude"
                    description="Remove players entirely from the returned lineups."
                    players={players}
                    selected={constraints.must_exclude}
                    loading={loadingPlayers}
                    onToggle={(playerId) => togglePlayer("must_exclude", playerId)}
                  />
                </div>
                <div className="grid gap-4 rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
                  <FilterNumber
                    label="Max non-shooters"
                    value={constraints.max_non_shooters}
                    onChange={(value) =>
                      setConstraints((current) => ({ ...current, max_non_shooters: parseNumber(value) }))
                    }
                    placeholder="e.g. 1"
                  />
                  <FilterNumber
                    label="Minimum player height"
                    value={constraints.min_size_score}
                    onChange={(value) =>
                      setConstraints((current) => ({ ...current, min_size_score: parseNumber(value) }))
                    }
                    placeholder="e.g. 79 inches"
                  />
                  <FilterNumber
                    label="Minimum trust"
                    value={constraints.min_trust}
                    onChange={(value) => setConstraints((current) => ({ ...current, min_trust: parseNumber(value) }))}
                    placeholder="0.0 to 1.0"
                  />
                </div>
              </CardContent>
            </Card>
          )}
        </section>

        <section ref={resultsRef} className="mt-12">
          {error && (
            <Card className="border-[#ff8f6b]/25 bg-[#ff8f6b]/10">
              <CardContent className="py-5 text-sm text-[#ffd2c4]">{error}</CardContent>
            </Card>
          )}

          {!response && !loading && !error && <EmptyState />}

          {loading && <LoadingState />}

          {response && !loading && (
            <div className="grid gap-8">
              <IntentSummary weights={response.parsed_intent.weights} constraints={response.parsed_intent.constraints} />
              <div className="grid gap-6 xl:grid-cols-3">
                {response.recommendations.map((recommendation) => (
                  <LineupCard key={`${recommendation.rank}-${recommendation.player_ids.join("-")}`} recommendation={recommendation} />
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function FilterGroup({
  title,
  description,
  players,
  selected,
  loading,
  onToggle,
}: {
  title: string;
  description: string;
  players: PlayerListItem[];
  selected: number[];
  loading: boolean;
  onToggle: (playerId: number) => void;
}) {
  return (
    <div className="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
      <div className="mb-4">
        <h3 className="font-display text-lg font-semibold text-white">{title}</h3>
        <p className="mt-1 text-sm text-white/60">{description}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {loading &&
          Array.from({ length: 8 }).map((_, index) => <Skeleton key={index} className="h-10 w-28 rounded-full" />)}
        {!loading &&
          players.map((player) => {
            const active = selected.includes(player.player_id);
            return (
              <Button
                key={player.player_id}
                variant="chip"
                className={cn(
                  "rounded-full border px-4 py-2",
                  active && "border-gold/50 bg-gold/12 text-gold",
                )}
                onClick={() => onToggle(player.player_id)}
              >
                {player.name}
              </Button>
            );
          })}
      </div>
    </div>
  );
}

function FilterNumber({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value?: number;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <label className="grid gap-2">
      <span className="text-sm font-semibold text-white/80">{label}</span>
      <Input
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
        className="bg-white/[0.06]"
        placeholder={placeholder}
        inputMode="decimal"
      />
    </label>
  );
}

function IntentSummary({
  weights,
  constraints,
}: {
  weights: IntentWeights;
  constraints: QueryConstraints;
}) {
  const [expanded, setExpanded] = useState(false);
  const summarySignature = JSON.stringify({ weights, constraints });

  useEffect(() => {
    setExpanded(false);
  }, [summarySignature]);

  const topPriorities = Object.entries(weights)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2);
  const activeConstraintCount = [
    constraints.must_include.length > 0,
    constraints.must_exclude.length > 0,
    constraints.max_non_shooters != null,
    constraints.min_size_score != null,
    constraints.min_trust != null,
  ].filter(Boolean).length;

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <CardTitle>Intent Summary</CardTitle>
            <div className="flex flex-wrap gap-2">
              {topPriorities.map(([key, value]) => (
                <Badge key={key} variant="subtle">
                  {metricLabels[key] ?? key}: {Math.round(value * 100)}%
                </Badge>
              ))}
              <Badge variant="subtle">
                {activeConstraintCount} active constraint{activeConstraintCount === 1 ? "" : "s"}
              </Badge>
            </div>
          </div>
          <Button variant="outline" className="self-start rounded-full lg:self-auto" onClick={() => setExpanded((current) => !current)}>
            {expanded ? "Hide details" : "Show details"}
          </Button>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <div className="grid gap-3">
            {Object.entries(weights).map(([key, value]) => (
              <div key={key} className="grid gap-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-white/78">{metricLabels[key] ?? key}</span>
                  <span className="text-gold">{Math.round(value * 100)}%</span>
                </div>
                <Progress value={value * 100} tone={key === "defense" ? "blue" : key === "size" ? "purple" : "gold"} />
              </div>
            ))}
          </div>
          <div className="grid gap-3 rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
            <Badge variant="subtle">Active constraints</Badge>
            <ConstraintLine label="Must include" value={constraints.must_include.length ? constraints.must_include.join(", ") : "None"} />
            <ConstraintLine label="Must exclude" value={constraints.must_exclude.length ? constraints.must_exclude.join(", ") : "None"} />
            <ConstraintLine label="Max non-shooters" value={constraints.max_non_shooters ?? "None"} />
            <ConstraintLine label="Min player height" value={constraints.min_size_score ?? "None"} />
            <ConstraintLine label="Min trust" value={constraints.min_trust ?? "None"} />
          </div>
        </CardContent>
      )}
    </Card>
  );
}

function ConstraintLine({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-white/58">{label}</span>
      <span className="font-semibold text-white">{value}</span>
    </div>
  );
}

function LineupCard({ recommendation }: { recommendation: Recommendation }) {
  const keyMetrics = Object.entries(recommendation.component_scores).filter(([key]) =>
    ["defense", "spacing", "shooting", "size", "playmaking"].includes(key),
  );

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-gold via-[#ffe39f] to-lilac" />
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <Badge variant="gold">#{recommendation.rank}</Badge>
              <Badge variant={recommendation.historical_seen ? "default" : "caution"}>
                {recommendation.historical_seen ? "Historical lineup" : "Generated lineup"}
              </Badge>
            </div>
            <CardTitle className="mt-4">Lineup {recommendation.rank}</CardTitle>
          </div>
          <div className="rounded-[22px] border border-gold/20 bg-gold/10 px-4 py-3 text-right">
            <p className="text-xs uppercase tracking-[0.22em] text-gold/70">Blend score</p>
            <p className="font-display text-3xl font-bold text-white">{formatScore(recommendation.score)}</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-5">
        <div className="grid gap-3">
          <div className="flex items-center justify-between">
            <h4 className="font-display text-lg font-semibold text-white">Player cards</h4>
            <Badge variant="subtle">{recommendation.players.length} players</Badge>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {recommendation.players.map((player) => (
              <PlayerCardView key={player.player_id} player={player} />
            ))}
          </div>
        </div>

        <div className="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-white/45">Fit read</p>
          <p className="mt-2 text-sm leading-6 text-white/80">{recommendation.reasoning}</p>
        </div>

        <Separator />

        <div className="grid grid-cols-2 gap-3">
          <StatTile label="Trust" value={`${Math.round(recommendation.trust_score * 100)}%`} icon={<Shield className="h-4 w-4" />} />
          <StatTile label="Rotation" value={`${Math.round(recommendation.lineup_metadata.rotation_score * 100)}%`} icon={<Waves className="h-4 w-4" />} />
          <StatTile label="Net rating" value={formatNullable(recommendation.lineup_metadata.net_rating)} />
          <StatTile label="Minutes" value={String(recommendation.lineup_metadata.minutes_played)} />
        </div>

        <div className="grid gap-3">
          {keyMetrics.map(([key, value]) => (
            <div key={key} className="grid gap-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-white/68">{metricLabels[key] ?? key}</span>
                <span className="font-semibold text-white">{formatMetric(key, value)}</span>
              </div>
              <Progress value={metricPercent(key, value)} tone={key === "defense" ? "blue" : key === "size" ? "purple" : "gold"} />
            </div>
          ))}
        </div>

        <Separator />

        <div className="grid gap-3">
          <h4 className="font-display text-lg font-semibold text-white">Lineup insights</h4>
          <div className="grid gap-3">
            {recommendation.lineup_insights.map((insight) => (
              <div
                key={`${insight.label}-${insight.value}`}
                className={cn(
                  "rounded-[22px] border px-4 py-3",
                  insight.tone === "positive" && "border-gold/20 bg-gold/8",
                  insight.tone === "caution" && "border-[#ff8f6b]/20 bg-[#ff8f6b]/10",
                  insight.tone !== "positive" && insight.tone !== "caution" && "border-white/10 bg-white/[0.04]",
                )}
              >
                <p className="text-xs uppercase tracking-[0.18em] text-white/45">{insight.label}</p>
                <p className="mt-1 text-sm leading-6 text-white/82">{insight.value}</p>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PlayerCardView({ player }: { player: PlayerCard }) {
  const headshotUrl = getHeadshotUrl(player.name);
  const isSpacer = player.three_pct != null && player.three_pct >= 0.35;
  const secondaryBadge = player.games_played == null ? "GP N/A" : `GP ${player.games_played}`;

  return (
    <div className="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
      <div className="flex items-center justify-between gap-3">
        <Badge variant="subtle">#{player.player_id}</Badge>
        <div className="flex gap-2">
          <Badge variant="subtle">{secondaryBadge}</Badge>
        </div>
      </div>
      <div className="mt-4">
        <PlayerHeadshot name={player.name} headshotUrl={headshotUrl} />
      </div>
      <div className="mt-4">
        <p className="font-display text-lg font-semibold text-white">{player.name}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-white/52">
          <span>
            {player.position || "Unlisted position"}
            {player.height_inches ? ` • ${formatHeight(player.height_inches)}` : ""}
          </span>
          {isSpacer && (
            <span className="inline-flex items-center rounded-full bg-gold/14 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-gold">
              Spacer
            </span>
          )}
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <MiniStat label="3PT" value={player.three_pct == null ? "N/A" : `${Math.round(player.three_pct * 100)}%`} />
        <MiniStat label="MPG" value={player.minutes_per_game == null ? "N/A" : String(player.minutes_per_game)} />
        <MiniStat label="DBPM" value={player.dbpm == null ? "N/A" : String(player.dbpm)} />
        <MiniStat label="GP" value={player.games_played == null ? "N/A" : String(player.games_played)} />
      </div>
    </div>
  );
}

function PlayerHeadshot({ name, headshotUrl }: { name: string; headshotUrl: string | null }) {
  const fallbackUrl = getFallbackAvatarUrl(name);
  const [imageSrc, setImageSrc] = useState<string>(headshotUrl ?? fallbackUrl);

  useEffect(() => {
    setImageSrc(headshotUrl ?? fallbackUrl);
  }, [headshotUrl, fallbackUrl]);

  return (
    <div className="overflow-hidden rounded-[22px] border border-white/10 bg-gradient-to-br from-white/8 to-white/[0.03]">
      <img
        src={imageSrc}
        alt={name}
        className="h-32 w-full object-contain object-center"
        loading="lazy"
        onError={() => {
          if (imageSrc !== fallbackUrl) {
            setImageSrc(fallbackUrl);
          }
        }}
      />
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-black/15 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.16em] text-white/38">{label}</p>
      <p className="mt-1 text-sm font-semibold text-white">{value}</p>
    </div>
  );
}

function StatTile({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: ReactNode;
}) {
  return (
    <div className="rounded-[22px] border border-white/10 bg-white/[0.04] px-4 py-3">
      <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-white/40">
        {icon}
        <span>{label}</span>
      </div>
      <p className="mt-2 font-display text-xl font-semibold text-white">{value}</p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="grid gap-6 xl:grid-cols-3">
      {Array.from({ length: 3 }).map((_, index) => (
        <Card key={index}>
          <CardHeader>
            <Skeleton className="h-7 w-20" />
            <Skeleton className="h-8 w-40" />
            <Skeleton className="h-20 w-full" />
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid grid-cols-2 gap-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
            <Skeleton className="h-2.5 w-full" />
            <Skeleton className="h-2.5 w-5/6" />
            <div className="grid gap-3 sm:grid-cols-2">
              {Array.from({ length: 4 }).map((_, itemIndex) => (
                <Skeleton key={itemIndex} className="h-28 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <Card className="mx-auto max-w-4xl">
      <CardContent className="grid gap-5 py-10 text-center">
        <div className="grid gap-2">
          <h2 className="font-display text-3xl font-bold text-white">See the five-man answer before the analysis.</h2>
          <p className="mx-auto max-w-2xl text-white/66">
            Ask one matchup question and get three ranked lineup options with the player cards up front, followed by
            the stats and context behind each recommendation.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function parseNumber(value: string): number | undefined {
  if (!value.trim()) {
    return undefined;
  }
  const parsedValue = Number(value);
  return Number.isFinite(parsedValue) ? parsedValue : undefined;
}

function metricPercent(key: string, value: number): number {
  if (key === "defense") {
    return Math.min(value * 10000, 100);
  }
  if (key === "size" || key === "playmaking") {
    return Math.min(value, 100);
  }
  return Math.min(value * 100, 100);
}

function formatScore(value: number): string {
  return value.toFixed(2);
}

function formatNullable(value: number | null): string {
  return value == null ? "N/A" : value.toFixed(1);
}

function formatMetric(key: string, value: number): string {
  if (key === "defense") {
    return value.toFixed(4);
  }
  if (key === "size") {
    return value.toFixed(1);
  }
  if (key === "playmaking") {
    return value.toFixed(1);
  }
  return `${Math.round(value * 100)}%`;
}

function formatHeight(heightInches: number): string {
  const feet = Math.floor(heightInches / 12);
  const inches = heightInches % 12;
  return `${feet}'${inches}"`;
}

export default App;
