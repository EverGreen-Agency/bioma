export type Ring = "assess" | "trial" | "adopt" | "hold";
export type Quadrant = "languages" | "frameworks" | "tools" | "platforms-infra";

export interface Tech {
  id: string;
  name: string;
  quadrant: Quadrant;
  ring: Ring;
  note: string;
  adr: string;
  source: string;
}

export interface StackRadar {
  schema_version: string;
  updated_at: string;
  note: string;
  rings: Ring[];
  quadrants: Quadrant[];
  techs: Tech[];
}
