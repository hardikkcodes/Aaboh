/** Plain-language notes for each briefing rule: what it means and what to do. */
export const INSIGHT_EXPLAINERS: Record<string, { means: string; action: string }> = {
  official_alert_active: {
    means: "A government agency has issued a warning. Some warnings only name the state, so yours may not be affected.",
    action: "Read the original bulletin and follow official instructions.",
  },
  heat_stress: {
    means: "Humidity makes the heat harder on the body than the temperature suggests.",
    action: "Drink water often, rest in shade, and check on older people and children.",
  },
  rain_next_24h: {
    means: "Forecast rain over the city. More rain in less time raises the chance of waterlogging.",
    action: "Allow extra travel time and check the live map before leaving.",
  },
  air_quality_station: {
    means: "The nearest monitoring station is reading above the satisfactory level.",
    action: "If you have asthma or heart or lung trouble, keep outdoor effort short.",
  },
  verified_waterlogging: {
    means: "A moderator has checked recent reports of water on the roads.",
    action: "Use another route. Never walk or drive through water you can't judge.",
  },
  unverified_reports_recent: {
    means: "Residents have reported something that nobody has checked yet.",
    action: "Treat it as a hint, and confirm it on the live map if you can see it.",
  },
  satellite_lst_hotspots: {
    means: "Satellite images show which places have the hottest ground and rooftops.",
    action: "Use this to compare places. It is not the air temperature today.",
  },
  climate_annual_temperature: {
    means: "How the latest year compares with the 1991–2020 average for this area.",
    action: "This is background. It helps explain the longer trend, not today's weather.",
  },
};

export const LONG_TERM_ACTIONS = [
  "Plant or protect trees and shade on your street: green places stay cooler.",
  "Keep drains around your home clear before the monsoon.",
  "Plan outdoor work and travel for cooler hours as hot days increase.",
];
