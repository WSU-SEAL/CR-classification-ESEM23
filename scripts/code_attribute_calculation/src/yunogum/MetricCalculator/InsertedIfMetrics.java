package yunogum.MetricCalculator;

import java.util.Map;
import java.util.List;

import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.tree.Tree;

import yunogum.AstUtils;
import yunogum.InsertAction;
import yunogum.MetricRunner;
import yunogum.PythonFileData;

public  class InsertedIfMetrics extends IfMetrics{
    public void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData) {
        int insertedIfConditions = 0;
        for (Tree t : classifier.getInsertedDsts()) {
            if(t.getType().name.equals(AstUtils.IF_STMT) ){
                if(fileData.isInsertedNodeInExtendedRange(t)){
                    InsertAction insertion = fileData.dstTreeToSrcInsertActionMap.getOrDefault(t, null);
                    if(fileData.checkIfInFunctionScope(insertion.mappedSrcParent)) {
                        insertedIfConditions++;
                        MetricRunner.dlog("insertion in extended range :\n" + t.toTreeString());
                    }

                }else{
                    if(MetricRunner.DEBUG){
                        MetricRunner.dlog(fileData.getDstNodeParentOverlappingExtendedRange(t));
                        MetricRunner.dlog("insertion out of range :\n" + t.toTreeString());
                    }
                }

            }
            
            // MetricRunner.dlog(t);
            // MetricRunner.dlog("-----------");
            // MetricRunner.dlog(t.toTreeString());
        }
        metrics.put("insertedIfConditions", insertedIfConditions);
    }



    public void putHeader(List<String> headers){

        headers.add("insertedIfConditions");
    }


}