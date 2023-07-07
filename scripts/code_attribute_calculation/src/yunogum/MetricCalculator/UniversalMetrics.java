package yunogum.MetricCalculator;
import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Dictionary;
import java.util.Hashtable;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.List;

import org.hamcrest.core.IsInstanceOf;

import com.github.gumtreediff.*;
import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.tree.Tree;

import yunogum.PythonFileData;

public abstract class UniversalMetrics extends MetricCalculator{
    public  int filterRange(Iterable<Tree> iter, PythonFileData fileData, boolean isSrc){
        int count = 0;
        for (Tree t : iter) {
            if( (isSrc && !fileData.isSrcNodeInExtendedRange(t) && fileData.checkIfInFunctionScope((t))) ||
                (!isSrc && !fileData.isDstNodeInExtendedRange(t) )){
                continue;
            }
            count++;
        }
        return count;
    }

    public void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData) {
        // MetricRunner.dlog("SRC---------------------------------------------------:\n" + results.src);
        // MetricRunner.dlog("DST---------------------------------------------------:\n" + results.dst);

        //#TODO filter these within range
        metrics.put("anyDeleted", filterRange(classifier.getDeletedSrcs(), fileData, true));
        metrics.put("anyInserted", filterRange(classifier.getInsertedDsts(), fileData, false));
        metrics.put("getMovedSrcs",filterRange( classifier.getMovedSrcs(), fileData, true));
        metrics.put("UpdatedSrcs", filterRange(classifier.getUpdatedSrcs(), fileData, true));
    }



    public void putHeader(List<String> headers){
        headers.add("anyDeleted");
        headers.add("anyInserted");
        headers.add("getMovedSrcs");
        headers.add("UpdatedSrcs");
    }
}
