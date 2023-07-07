package yunogum.MetricCalculator;
import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Dictionary;
import java.util.HashSet;
import java.util.Hashtable;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.hamcrest.core.IsInstanceOf;

import com.github.gumtreediff.*;
import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.EditScript;
import com.github.gumtreediff.actions.EditScriptGenerator;
import com.github.gumtreediff.actions.SimplifiedChawatheScriptGenerator;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.actions.model.Action;
import com.github.gumtreediff.client.Client;
import com.github.gumtreediff.client.Clients;
import com.github.gumtreediff.client.Option;
import com.github.gumtreediff.client.Run;
import com.github.gumtreediff.client.Run.Options;
import com.github.gumtreediff.gen.Registry;
import com.github.gumtreediff.gen.TreeGenerators;
import com.github.gumtreediff.matchers.Mapping;
import com.github.gumtreediff.matchers.MappingStore;
import com.github.gumtreediff.matchers.Matcher;
import com.github.gumtreediff.matchers.Matchers;
import com.github.gumtreediff.tree.DefaultTree;
import com.github.gumtreediff.tree.Tree;

import yunogum.AstUtils;
import yunogum.PythonFileData;

public class StringAssignment extends MetricCalculator{
    public static void main(String[] origArgs) {
        Options opts = new Options();
        String[] args = Option.processCommandLine(origArgs, opts);

        Run.initClients();

        Registry.Factory<? extends Client> client;
        if (args.length == 0) {
            System.err.println("No command given.");
            Run.displayHelp(System.err, opts);
        } else if ((client = Clients.getInstance().getFactory(args[0])) == null) {
            System.err.printf("Unknown sub-command '%s'.\n", args[0]);
            Run.displayHelp(System.err, opts);
        } else {
            try{

                PrintStream console = System.out;

                File file = new File(".temp");
                FileOutputStream fos = new FileOutputStream(file);
                PrintStream ps = new PrintStream(fos);
                System.setOut(ps);
                
                Run.initGenerators(); // registers the available parsers
                // String srcFile = "a.py";
                // String dstFile = "b.py";
                String srcFile = args[1];
                String dstFile = args[2];
                Map<String, Integer> metrics = new Hashtable<>();
                Diff results = Diff.compute(srcFile, dstFile);
                // TreeClassifier classifier = results.createRootNodesClassifier();//we'll miss a lot of changes if we just get root ndoes that changed
                TreeClassifier classifier = results.createAllNodeClassifier();
                // Set<Tree> deletedSrcs = classifier.getDeletedSrcs(); 
                // TreeContext tc = TreeGenerators.getInstance().getTree(srcFile);
                // System.out.println(results.mappings.size());
                // System.out.println(tc);
                for(Mapping m: results.mappings ){
                    System.out.println(m.first + " \nmaps to:\n " + m.second);
                }
                StringAssignment stringAssignment = new StringAssignment();
                PythonFileData fileData = PythonFileData.parseFile(srcFile, dstFile, 0, results, classifier);
                stringAssignment.calc(metrics, results, classifier,fileData);

                for (Map.Entry<String, Integer> entry : metrics.entrySet()) {
                    String key = entry.getKey();
                    int val = entry.getValue();
                    System.out.println(key + " : " +val);
                }
            }catch(Exception e){
                System.out.println(e);
            }
        }
    }
    

    public void calc(Map<String, Integer> metrics, Diff results, TreeClassifier classifier, PythonFileData fileData){
        // System.out.println("SRC---------------------------------------------------:\n" + results.src);
        // System.out.println("DST---------------------------------------------------:\n" + results.dst);

        //get all strings in src, check if that string was part of any direct assignment inserted in dst
        //if so we have magic string refactoring
        //this does not get any strings that are made from str(object) calls
        //due python ducktyping we can't derive final assigned var type in compiletime.
        //this justs checks if node type == String


        //get plain string typed things in src
        Set<String> stringsInSrc = new HashSet<>();
        for(Tree t: results.src.getRoot().preOrder()){
            if(AstUtils.isTreeType(t, AstUtils.STRING)){
                stringsInSrc.add(t.getLabel());
            }
        }
        int magicStringsReplaced = 0;
        for(Tree t: classifier.getInsertedDsts()){
            if(fileData.checkIfInFunctionScope(t)) {
                // only a = "str". nothing more complicated than that is not possible since
                // python does not have copile time type info
                // you could produce strings via str() calls but strings like that are not
                // necessarily indicators of
                if (AstUtils.isTreeType(t, AstUtils.EXPR_STMT) &&
                        t.getChildren().size() == 3 &&
                        (AstUtils.isTreeType(t.getChild(1), AstUtils.OPERATOR)
                                && AstUtils.hasLabel(t.getChild(1), AstUtils.EQUALS))
                        &&
                        AstUtils.isTreeType(t.getChild(2), AstUtils.STRING)) {
                    Tree asignedVar = t.getChild(0);
                    Tree operator = t.getChild(1);
                    Tree assignmentVal = t.getChild(2);
                    // System.out.println(asignedVar + " " + operator+" "+assignmentVal);
                    if (stringsInSrc.contains(assignmentVal.getLabel())) {
                        // System.out.println("magic string replace " + assignmentVal );
                        magicStringsReplaced++;
                    }
                }
            }
        }
        metrics.put("magicStringsReplaced", magicStringsReplaced);
    }
    public void putHeader(List<String> headers){
        headers.add("magicStringsReplaced");
    }



}