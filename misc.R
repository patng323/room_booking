# Convert wide facility CSV file to input for SQL
library(data.table)
library(tidyr)

dt <- fread("~/Downloads/truth_fac.csv")
dt2 <- data.table(gather(dt, key="fac", value="value", 高映機:電視))
dt2 <- dt2[value==1]
write.csv(dt2, "~/Downloads/truth_fac_import.csv", row.names = F)