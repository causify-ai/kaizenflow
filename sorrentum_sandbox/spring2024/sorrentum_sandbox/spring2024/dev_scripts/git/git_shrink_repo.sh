if [[ 1 == 0 ]]; then
git rev-list --objects --all | sort -k 2 > allfileshas.txt

git gc && git verify-pack -v .git/objects/pack/pack-*.idx | egrep "^\w+ blob\W+[0-9]+ [0-9]+ [0-9]+$" | sort -k 3 -n -r > bigobjects.txt

for SHA in `cut -f 1 -d\  < bigobjects.txt`; do
    echo $(grep $SHA bigobjects.txt) $(grep $SHA allfileshas.txt) | awk '{print $1,$3,$7}' >> bigtosmall.txt
done;
fi;

if [[ 1 == 1 ]]; then
    BIG_FILES="core/test/TestGluonAdapter.test_inverse_transform/output/test.txt core/dataflow_model/notebooks/Master_strategy_analyzer.ipynb core/notebooks/gallery_signal_processing.ipynb im/kibot/data/extract/test/TestKibotDownload.test_extract_payload_links/input/all_stocks_1min.html vendors/kibot/data/kibot_metadata/All_Futures_Contracts_daily.csv core/notebooks/gallery_signal_processing.ipynb amp_research/PartTask275_PRICE_Explore_Kibot_contracts.ipynb core/notebooks/gallery_signal_processing.ipynb amp_research/PartTask275_PRICE_Explore_Kibot_contracts.ipynb core/notebooks/gallery_signal_processing.ipynb vendors/kibot/Task269_Top_oil_futures_by_liquidity.ipynb core/notebooks/gallery_signal_processing.ipynb amp_research/PartTask461_One_instrument_analysis.ipynb vendors/kibot/Task269_Top_oil_futures_by_liquidity.ipynb core/notebooks/gallery_signal_processing.ipynb vendors/particle_one/Task269_Top_oil_futures_by_liquidity.ipynb amp_research/PartTask461_One_instrument_analysis.ipynb instrument_master/kibot/notebooks/gallery_kibot.ipynb vendors_amp/kibot/notebooks/gallery_kibot.ipynb amp_research/PartTask275_PRICE_Explore_Kibot_contracts.ipynb"
    git filter-branch -f --prune-empty --index-filter "git rm -rf --cached --ignore-unmatch $BIG_FILES" --tag-name-filter cat -- --all
    git gc --aggressive --prune=all
fi;
