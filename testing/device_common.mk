# LMKD property
PRODUCT_PROPERTY_OVERRIDES += \
    ro.slmk.dha_cached_min=2 \
    ro.slmk.dha_empty_max=24 \
    ro.slmk.dha_empty_limit=24 \
    ro.slmk.dha_2ndprop_thMB=6144 \
    ro.slmk.add_bonusEFK=2 \
    ro.slmk.v_bonusEFK=81920 \
    ro.slmk.2nd.swap_free_low_percentage=35 \
    ro.slmk.beks_enable=true \
    ro.slmk.max_snapshot_num=4 \
    ro.slmk.dec_EFK_enable=true \
    ro.slmk.trim_sec_policy=true

# LMKD property
ifneq ($(filter %zn %ctc %zm %zc %zcx, $(TARGET_PRODUCT)), )
PRODUCT_PROPERTY_OVERRIDES += \
    ro.slmk.swap_free_low_percentage=25 \
    ro.slmk.psi_critical=150 \
    ro.slmk.chimera_strategy_6gb=1350,18,9,2034 \
    ro.slmk.plg_key=4101 \
    ro.slmk.dha_pwhl_key=512 \
    ro.slmk.cam_dha_ver=3
else
PRODUCT_PROPERTY_OVERRIDES += \
    ro.slmk.swap_free_low_percentage=43 \
    ro.slmk.psi_critical=130 \
    ro.slmk.chimera_strategy_6gb=1350,15,9,2034 \
    ro.slmk.freelimit_val=11 \
    ro.slmk.2nd.freelimit_val=13 \
    ro.slmk.plg_key=74756 \
    ro.slmk.dha_pwhl_key=514 \
    ro.slmk.cam_dha_ver=19
endif

# Nandswap
PRODUCT_PROPERTY_OVERRIDES += \
    ro.sys.kernelmemory.nandswap.slot_count_map=5,6,8,8,12 \
    ro.sys.kernelmemory.nandswap.writeback_on_bg=true \
    ro.sys.kernelmemory.nandswap.expand_action=true \
    ro.sys.kernelmemory.nandswap.prefetch_action=true \
    ro.sys.kernelmemory.nandswap.storage_clock_boost=true

# Chimera property
PRODUCT_PROPERTY_OVERRIDES += \
    ro.slmk.chimera_strategy_8gb=2300,20,9,2550