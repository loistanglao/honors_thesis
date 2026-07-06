library(fixest)
library(readr)

df <- read_csv("~/Documents/honors_thesis/data/processed/merged_18_19_21.csv")

model_simple_fe <- feols(bmi ~ yam_suitability | enns_year,
                data = df)
summary(model_simple_fe)

model_simple <- feols(bmi ~ yam_suitability + ube_price_1kg,
                      data = df)
summary(model_simple)

model_interaction <- feols(bmi ~ yam_suitability + ube_price_1kg + yam_suitability:ube_price_1kg,
               data = df,
               cluster = ~provhuc)
summary(model_interaction)

# Save as HTML first
etable(model_simple_fe, model_simple, model_interaction,
       file = "~/Documents/honors_thesis/output/model_table.html")

### SAVE TO PNG
library(modelsummary)


modelsummary(
  list("FE" = model_simple_fe, "Simple" = model_simple, "Clustered" = model_interaction),
  output = "~/Documents/honors_thesis/output/model_table.png",
  stars = TRUE,
  gof_omit = "AIC|BIC|Log",
  fmt = 8 # number of decimal places
)


