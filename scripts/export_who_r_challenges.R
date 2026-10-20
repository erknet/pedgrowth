# Independent WHO R oracle: vectorized by table, with all missing outputs
# retained for investigation. This script never imports GrowthCharts.
args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 2L) stop('Usage: Rscript export_who_r_challenges.R INPUT OUTPUT')
if (!requireNamespace('anthro', quietly=TRUE) ||
    !requireNamespace('anthroplus', quietly=TRUE)) stop('WHO anthro R packages required')
d <- read.csv(args[1], stringsAsFactors=FALSE)
d$expected <- NA_real_
d$engine <- NA_character_
for (table in unique(d$table)) {
  rows <- which(d$table == table)
  r <- d[rows,]
  kind <- r$indicator[1]
  is_2007 <- startsWith(table, 'who2007_')
  if (is_2007) {
    heights <- if (kind == 'hfa') r$measurement else rep(100, nrow(r))
    weights <- if (kind == 'wfa') r$measurement else if (kind == 'bmifa') r$measurement else rep(30, nrow(r))
    out <- anthroplus::anthroplus_zscores(
       sex=r$sex, age_in_months=r$coordinate,
       height_in_cm=heights, weight_in_kg=weights)
    key <- switch(kind, hfa='zhfa', wfa='zwfa', bmifa='zbfa')
    d$expected[rows] <- out[[key]]
    d$engine[rows] <- paste0('WHO anthroplus ', as.character(utils::packageVersion('anthroplus')))
  } else {
    isage <- kind %in% c('wfa','lfa','hfa','hcfa','bmifa','muacfa','tsfa','ssfa')
    days <- if (isage) r$coordinate * 30.4375 else if (kind=='wfh') rep(900,nrow(r)) else rep(365,nrow(r))
    lenhei <- if (kind %in% c('lfa','hfa')) r$measurement else if (kind %in% c('wfl','wfh')) r$coordinate else rep(80,nrow(r))
    weight <- if (kind %in% c('wfa','wfl','wfh')) r$measurement else if (kind=='bmifa') r$measurement*(lenhei/100)^2 else rep(10,nrow(r))
    measure <- ifelse(kind %in% c('hfa','wfh') | (isage & days>=731), 'H', 'L')
    out <- anthro::anthro_zscores(
       sex=r$sex, age=days, weight=weight, lenhei=lenhei, measure=measure,
       headc=if (kind=='hcfa') r$measurement else rep(45,nrow(r)),
       armc=if (kind=='muacfa') r$measurement else rep(15,nrow(r)),
       triskin=if (kind=='tsfa') r$measurement else rep(10,nrow(r)),
       subskin=if (kind=='ssfa') r$measurement else rep(10,nrow(r)))
    key <- switch(kind,wfa='zwei',lfa='zlen',hfa='zlen',hcfa='zhc',bmifa='zbmi',
                  wfl='zwfl',wfh='zwfl',muacfa='zac',tsfa='zts',ssfa='zss')
    d$expected[rows] <- out[[key]]
    d$engine[rows] <- paste0('WHO anthro ', as.character(utils::packageVersion('anthro')))
  }
}
write.csv(d, args[2], row.names=FALSE, na='')
cat('Challenges',nrow(d),'non-NA',sum(is.finite(d$expected)),
    'missing',sum(!is.finite(d$expected)),'\n')
